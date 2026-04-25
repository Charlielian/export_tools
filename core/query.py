# -*- coding: utf-8 -*-
"""
数据查询模块
负责即席查询、数据获取和分批处理
"""

import requests
import json
import random
import time

from urllib.parse import urlencode

from utils.config import (
    BASE_URL, JXCX_URL, JXCX_COUNT_URL, JXCX_SEARCH_URL, JXCX_TABLE_URL,
    HEADERS, MAX_SINGLE_QUERY
)


class JXCXQuery:
    """即席查询类"""

    def __init__(self, session):
        self.sess = session
        self.enabled = False
        self._field_config_cache = {}

    def get_field_config(self, table_key, fieldtype, api_type='search'):
        """动态获取表字段配置（从API获取）"""
        cache_key = f"{table_key}_{fieldtype}_{api_type}"
        if cache_key in self._field_config_cache:
            print(f"[DEBUG-FIELD] 使用缓存的字段配置: {cache_key}")
            return self._field_config_cache[cache_key]

        print(f"[DEBUG-FIELD] 动态获取字段配置: table_key={table_key}, fieldtype={fieldtype}, api_type={api_type}")

        try:
            if api_type == 'table':
                data = {'tablename': table_key}
                res = self.sess.post(JXCX_TABLE_URL, data=data, headers=HEADERS, timeout=30)

                if res.status_code == 200:
                    result = json.loads(res.content)
                    configs = result.get('CFG_ADHOC_CONF_TABLE', [])
                    print(f"[DEBUG-FIELD] 从getSelectTable接口获取到 {len(configs)} 个字段配置")

                    self._field_config_cache[cache_key] = configs
                    return configs
                else:
                    print(f"[ERROR-FIELD] 获取字段配置失败: {res.status_code}")
                    return None
            else:
                data = {
                    'key': table_key,
                    'field': 'columnname_cn',
                    'field': 'columnname',
                    'field': 'fieldtype',
                    'field': 'datatype',
                    'field': 'tablename',
                    'field': 'tablename_cn',
                    'field': 'columntype',
                    'field': 'sort'
                }
                res = self.sess.post(JXCX_SEARCH_URL, data=data, headers=HEADERS, timeout=30)

                if res.status_code == 200:
                    result = json.loads(res.content)
                    configs = result.get('CFG_ADHOC_CONF_SEARCH', [])
                    print(f"[DEBUG-FIELD] 从search接口获取到 {len(configs)} 个字段配置")

                    self._field_config_cache[cache_key] = configs
                    return configs
                else:
                    print(f"[ERROR-FIELD] 获取字段配置失败: {res.status_code}")
                    return None
        except Exception as e:
            print(f"[ERROR-FIELD] 获取字段配置异常: {e}")
            return None

    def build_payload_from_config(self, table_key, fieldtype, where_conditions, api_type='search'):
        """从动态获取的字段配置构建payload"""
        configs = self.get_field_config(table_key, fieldtype, api_type)
        if not configs:
            return None

        print(f"[DEBUG-PAYLOAD] API返回的字段配置数量: {len(configs)}")
        print(f"[DEBUG-PAYLOAD] API返回的字段名(前10个): {[c.get('columnname', '') for c in configs[:10]]}")
        print(f"[DEBUG-PAYLOAD] API返回的fieldtype(前3个): {list(set(c.get('fieldtype', '') for c in configs[:3]))}")

        sorted_configs = sorted(configs, key=lambda x: x.get('sort', 0))

        first_config = sorted_configs[0]
        geographicdimension = first_config.get('geographicdimension', '小区')
        timedimension = first_config.get('timedimension', '天')
        enodeb_field = first_config.get('enodeb_field', 'enodeb_id')
        cgi_field = first_config.get('cgi_field', 'cgi')
        time_field = first_config.get('time_field', 'starttime')
        cell_field = first_config.get('cell_field', 'cell')
        city_field = first_config.get('city_field', 'city')

        print(f"[DEBUG-PAYLOAD] 从API获取维度参数:")
        print(f"  geographicdimension: {geographicdimension}")
        print(f"  timedimension: {timedimension}")
        print(f"  enodebField: {enodeb_field}")
        print(f"  cgiField: {cgi_field}")
        print(f"  timeField: {time_field}")
        print(f"  cellField: {cell_field}")
        print(f"  cityField: {city_field}")

        field_list = [c['columnname'] for c in sorted_configs]

        columns = []
        for field in field_list:
            columns.append({
                'data': field,
                'name': '',
                'searchable': True,
                'orderable': True,
                'search': {'value': '', 'regex': False}
            })

        table_name = first_config.get('tablename', '')
        table_name_cn = first_config.get('tablename_cn', '')
        supporteddimension = first_config.get('supporteddimension')
        supportedtimedimension = first_config.get('supportedtimedimension', '')

        result_list = []
        for c in sorted_configs:
            result_list.append({
                'feildtype': c.get('fieldtype', ''),
                'table': c.get('tablename', ''),
                'tableName': c.get('tablename_cn', ''),
                'datatype': c.get('datatype', 'character varying'),
                'columntype': c.get('columntype', 1),
                'feildName': c.get('columnname_cn', ''),
                'feild': c.get('columnname', ''),
                'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'
            })

        result = {
            'result': result_list,
            'tableParams': {
                'supporteddimension': supporteddimension,
                'supportedtimedimension': supportedtimedimension
            },
            'columnname': ''
        }

        payload = {
            'draw': 1,
            'start': 0,
            'length': 200,
            'total': 0,
            'geographicdimension': geographicdimension,
            'timedimension': timedimension,
            'enodebField': enodeb_field,
            'cgiField': cgi_field,
            'timeField': time_field,
            'cellField': cell_field,
            'cityField': city_field,
            'columns': columns,
            'order': [{'column': 0, 'dir': 'desc'}],
            'search': {'value': '', 'regex': False},
            'result': result,
            'where': where_conditions,
            'indexcount': 0
        }

        print(f"[DEBUG-PAYLOAD] 构建的payload包含 {len(columns)} 个字段")
        return payload

    def enter_jxcx(self, retry_times=3, timeout=60):
        """进入即席查询模块"""
        print("\n[DEBUG-JXCX] ========== 进入即席查询模块 ==========")

        for attempt in range(retry_times):
            if attempt > 0:
                print(f"\n[DEBUG-JXCX] 重试第 {attempt} 次...")

            try:
                castgc = self.sess.cookies.get('CASTGC', domain='nqi.gmcc.net')
                if not castgc:
                    castgc = self.sess.cookies.get('CASTGC')

                if not castgc:
                    print("[ERROR-JXCX] 未找到CASTGC cookie")
                    continue

                print(f"[DEBUG-JXCX] CASTGC获取成功: {castgc[:20]}...")

                url = f'{BASE_URL}/pro-portal/pure/urlAction.action'
                params = {
                    'url': 'pro-adhoc/index',
                    'random': random.random(),
                    '__PID': 'JXCX',
                    'token': castgc
                }

                url_with_params = f"{url}?url={params['url']}&__PID={params['__PID']}&random={params['random']}&token={params['token']}"
                print(f"[DEBUG-JXCX] 请求URL: {url_with_params[:200]}...")

                start_time = time.time()
                res = self.sess.get(url_with_params, headers=HEADERS, timeout=timeout)
                elapsed_time = time.time() - start_time

                print(f"[DEBUG-JXCX] 响应状态码: {res.status_code}, 耗时: {elapsed_time:.2f}秒")

                if res.status_code == 200:
                    self.enabled = True
                    print("[SUCCESS-JXCX] 即席查询模块初始化成功！")
                    return True
                else:
                    print(f"[ERROR-JXCX] 进入即席查询失败，状态码: {res.status_code}")
                    continue

            except requests.exceptions.Timeout:
                print(f"[ERROR-JXCX] 请求超时 (timeout={timeout}s)")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"[ERROR-JXCX] 网络连接错误: {e}")
                continue
            except Exception as e:
                print(f"[ERROR-JXCX] 未知错误: {e}")
                continue

        print(f"[ERROR-JXCX] 进入即席查询失败，已尝试 {retry_times} 次")
        return False

    def get_table_count(self, payload):
        """获取查询结果行数"""
        if not self.enabled:
            self.enter_jxcx()

        key_list = ['geographicdimension', 'timedimension', 'enodebField', 'cgiField',
                    'timeField', 'cellField', 'cityField', 'result', 'where', 'indexcount',
                    'columns', 'order', 'search']
        payload_count = {key: value for key, value in payload.items() if key in key_list}
        payload_encoded = self._encode_payload(payload_count)

        print(f"[DEBUG-COUNT] 查询总数 URL: {JXCX_COUNT_URL}")
        print(f"[DEBUG-COUNT] 查询参数 (前500字符): {payload_encoded[:500]}...")

        try:
            res = self.sess.post(JXCX_COUNT_URL, data=payload_encoded, headers=HEADERS, timeout=180)
            print(f"[DEBUG-COUNT] 响应状态码: {res.status_code}")

            if res.status_code == 200:
                if not res.content or len(res.content.strip()) == 0:
                    print(f"[ERROR-COUNT] 响应内容为空，可能是Session过期")
                    self.enabled = False
                    return 0

                try:
                    result = json.loads(res.content)
                except json.JSONDecodeError as e:
                    print(f"[ERROR-COUNT] JSON解析失败: {e}")
                    print(f"[ERROR-COUNT] 响应内容 (前500字符): {res.text[:500]}")
                    self.enabled = False
                    return 0

                print(f"[DEBUG-COUNT] 响应内容: {result}")

                if 'message' in result and result['message']:
                    msg = str(result['message'])
                    print(f"[WARNING-COUNT] 服务器返回消息: {msg}")
                    if '不存在' in msg:
                        print(f"[WARNING-COUNT] 数据不存在，返回0")
                        return 0

                count = result.get('count', result.get('data', {}).get('total', 1000000))
                print(f"[DEBUG-COUNT] 查询到的数据行数: {count}")
                return count
        except Exception as e:
            print(f"[ERROR-COUNT] 查询异常: {e}")
            import traceback
            traceback.print_exc()
            pass

        print(f"[WARNING-COUNT] 查询超时，返回MAX_SINGLE_QUERY({MAX_SINGLE_QUERY})")
        return MAX_SINGLE_QUERY

    def _encode_payload(self, payload):
        """URL编码payload"""
        result = []
        for key, value in payload.items():
            if isinstance(value, dict):
                encoded_value = json.dumps(value, ensure_ascii=False)
                result.append((key, encoded_value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        encoded_item = json.dumps(item, ensure_ascii=False)
                        result.append((key, encoded_item))
                    else:
                        result.append((key, str(item)))
            else:
                result.append((key, str(value) if value is not None else ''))
        return urlencode(result, safe='', encoding='utf-8')

    def get_table(self, payload, to_df=True):
        """获取表格数据"""
        import pandas as pd

        if not self.enabled:
            print("[DEBUG-TABLE] JXCX 未启用，尝试进入...")
            if not self.enter_jxcx():
                print("[ERROR-TABLE] 无法进入即席查询模块")
                return pd.DataFrame() if to_df else {'data': []}

        payload_encoded = self._encode_payload(payload)

        try:
            res = self.sess.post(JXCX_URL, data=payload_encoded, headers=HEADERS, timeout=180)

            if res.status_code == 200:
                result = json.loads(res.content)

                if 'data' in result and result['data']:
                    data = result['data']
                    if to_df:
                        df = pd.DataFrame(data)
                        print(f"[SUCCESS-TABLE] 获取到 {len(df)} 行数据")
                        return df
                    else:
                        return {'data': data}
                else:
                    print("[WARNING-TABLE] 返回数据为空")
                    return pd.DataFrame() if to_df else {'data': []}
            else:
                print(f"[ERROR-TABLE] 请求失败，状态码: {res.status_code}")
                return pd.DataFrame() if to_df else {'data': []}

        except Exception as e:
            print(f"[ERROR-TABLE] 获取数据异常: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame() if to_df else {'data': []}

    def get_4g_voice_table(self, volte_payload, epsfb_payload, to_df=True):
        """获取4G语音小区报表数据（VoLTE+EPSFB联合）"""
        result = self._get_4g_voice_table_internal(volte_payload, epsfb_payload)
        if to_df:
            return result['merged']
        else:
            return {'data': result['merged'].to_dict('records')}

    def _get_4g_voice_table_internal(self, volte_payload, epsfb_payload):
        """获取4G语音小区报表数据（内部方法）"""
        import pandas as pd
        import numpy as np

        result = {'volte': pd.DataFrame(), 'epsfb': pd.DataFrame(), 'merged': pd.DataFrame()}

        if not self.enabled:
            print("[DEBUG-4G-VOICE] JXCX 未启用，尝试进入...")
            if not self.enter_jxcx():
                print("[ERROR-4G-VOICE] 无法进入即席查询模块")
                return result

        print(f"[DEBUG-4G-VOICE] ========== 开始获取4G语音小区数据 ==========")

        print("[DEBUG-4G-VOICE] 正在获取VoLTE数据...")
        volte_df = self.get_table(volte_payload, to_df=True)
        print(f"[DEBUG-4G-VOICE] VoLTE数据: {len(volte_df)} 行")
        print(f"[DEBUG-4G-VOICE] VoLTE列名: {list(volte_df.columns) if not volte_df.empty else 'N/A'}")
        result['volte'] = volte_df

        print("[DEBUG-4G-VOICE] 正在获取EPSFB数据...")
        epsfb_df = self.get_table(epsfb_payload, to_df=True)
        print(f"[DEBUG-4G-VOICE] EPSFB数据: {len(epsfb_df)} 行")
        print(f"[DEBUG-4G-VOICE] EPSFB列名: {list(epsfb_df.columns) if not epsfb_df.empty else 'N/A'}")
        result['epsfb'] = epsfb_df

        if volte_df.empty and epsfb_df.empty:
            print("[WARNING-4G-VOICE] VoLTE和EPSFB数据均为空")
            return result

        col_name_map = {
            'starttime': '时间', 'city': '地市', 'cgi': '小区', 'grid': '责任网格',
            'area': '区县', 'nrcell_name': '小区名称'
        }

        volte_rename = {}
        for en_col in volte_df.columns:
            if en_col in col_name_map:
                volte_rename[en_col] = col_name_map[en_col]
        volte_df = volte_df.rename(columns=volte_rename)

        epsfb_rename = {}
        for en_col in epsfb_df.columns:
            if en_col in col_name_map:
                epsfb_rename[en_col] = col_name_map[en_col]
        epsfb_df = epsfb_df.rename(columns=epsfb_rename)

        print(f"[DEBUG-4G-VOICE] VoLTE转换后列名: {list(volte_df.columns)}")
        print(f"[DEBUG-4G-VOICE] EPSFB转换后列名: {list(epsfb_df.columns)}")

        merge_keys = []
        for key in ['时间', '小区']:
            if key in volte_df.columns:
                merge_keys.append(key)

        print(f"[DEBUG-4G-VOICE] 合并键: {merge_keys}")

        if not merge_keys:
            print("[WARNING-4G-VOICE] 无法确定合并键，使用简单concat")
            merged_df = pd.concat([volte_df, epsfb_df], ignore_index=True)
            result['merged'] = merged_df
            return result

        common_cols = set(['时间', '小区', '地市', '责任网格', '区县', 'starttime', 'city', 'cgi', 'grid', 'area', 'nrcell_name'])
        volte_cols = [c for c in volte_df.columns if (c.startswith('volte_') or 'VoLTE' in c) and c not in common_cols]
        epsfb_cols = [c for c in epsfb_df.columns if (c.startswith('epsfb_') or 'EPSFB' in c) and c not in common_cols]

        print(f"[DEBUG-4G-VOICE] VoLTE特有字段: {volte_cols}")
        print(f"[DEBUG-4G-VOICE] EPSFB特有字段: {epsfb_cols}")

        volte_merge_cols = [c for c in merge_keys if c in volte_df.columns] + [c for c in volte_cols if c in volte_df.columns]
        if '小区名称' in volte_df.columns:
            volte_merge_cols.append('小区名称')
        volte_for_merge = volte_df[volte_merge_cols].copy()

        epsfb_merge_cols = [c for c in merge_keys if c in epsfb_df.columns] + [c for c in epsfb_cols if c in epsfb_df.columns]
        if '小区名称' in epsfb_df.columns:
            epsfb_merge_cols.append('小区名称')
        epsfb_for_merge = epsfb_df[epsfb_merge_cols].copy()
        if '小区名称' in epsfb_for_merge.columns:
            epsfb_for_merge = epsfb_for_merge.rename(columns={'小区名称': '小区名称_epsfb'})

        if not merge_keys:
            merged_df = pd.concat([volte_for_merge, epsfb_for_merge], axis=1)
        else:
            merged_df = pd.merge(volte_for_merge, epsfb_for_merge, on=merge_keys, how='outer')

        if '小区名称_epsfb' in merged_df.columns:
            if '小区名称' not in merged_df.columns:
                merged_df['小区名称'] = merged_df['小区名称_epsfb']
            else:
                merged_df['小区名称'] = merged_df['小区名称'].fillna(merged_df['小区名称_epsfb'])
            merged_df = merged_df.drop(columns=['小区名称_epsfb'])
            print(f"[DEBUG-4G-VOICE] 小区名称已补充（VoLTE优先，EPSFB备用）")

        merged_df = merged_df.dropna(axis=1, how='all')

        cols = list(merged_df.columns)
        if '小区名称' in cols and '小区' in cols:
            cols.remove('小区名称')
            xiaoqu_idx = cols.index('小区')
            cols.insert(xiaoqu_idx + 1, '小区名称')
            merged_df = merged_df[cols]
            print(f"[DEBUG-4G-VOICE] 已将小区名称列移到小区列后面")

        print(f"[SUCCESS-4G-VOICE] 合并完成，最终数据: {len(merged_df)} 行, {len(merged_df.columns)} 列")
        result['merged'] = merged_df
        return result
