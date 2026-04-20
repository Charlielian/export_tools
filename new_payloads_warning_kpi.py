#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动生成的payload函数 - 监控预警和KPI报表"""

def get_volte_warning_payload():
    """获取VoLTE小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 VoLTE小区监控预警 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '初始注册成功率（控制面）', 'feild': 'cs_reg1_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE注册成功率（控制面）', 'feild': 'cs_reg_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE用户面丢包率', 'feild': 'volte_user_pkt_loss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE用户面时延（秒）', 'feild': 'volte_user_delay', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE接通率', 'feild': 'volte_connect_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE掉话率', 'feild': 'volte_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ESRVCC切换成功率', 'feild': 'esrvcc_ho_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE语音话务量（Erl）', 'feild': 'volte_voice_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE视频话务量（Erl）', 'feild': 'volte_video_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE语音QCI=1承载成功率', 'feild': 'volte_voice_qci1_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE视频QCI=2承载成功率', 'feild': 'volte_video_qci2_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ERAB建立成功率', 'feild': 'erab_setup_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ERAB掉线率', 'feild': 'erab_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VoLTE小区监控预警数据表-天', 'table': 'csem.f_nk_volte_keykpi_cell_d', 'tableName': 'VoLTE小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'RRC连接建立成功率', 'feild': 'rrc_setup_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_epsfb_warning_payload():
    """获取EPSFB小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 EPSFB小区监控预警 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': '---', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+始呼网络接通率(SA控制起始)', 'feild': 'sacs_start_moc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+终呼网络接通率(SA控制起始)', 'feild': 'sacs_start_mtc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+始呼网络接通率(CSCF控制起始)', 'feild': 'saccs_start_moc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPS+FB+终呼网络接通率(CSCF控制起始)', 'feild': 'saccs_start_mtc_net_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPSFB语音话务量(Erl)', 'feild': 'epsfb_voice_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'EPSFB掉话率', 'feild': 'epsfb_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoLTE呼迁成功率', 'feild': 'volte_ho_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'EPSFB小区监控预警数据表-天', 'table': 'csem.f_nk_epsfb_keykpi_cell_d', 'tableName': 'EPSFB小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'ESRVCC切换成功率', 'feild': 'esrvcc_ho_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_vonr_warning_payload():
    """获取VONR小区监控预警payload"""
    print("[DEBUG-PAYLOAD] 生成 VONR小区监控预警 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区', 'timedimension': '天',
        'enodebField': 'gnodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF初始注册成功率（SA控制起始）', 'feild': 'sacs_start_reg_init_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF注册成功率[含重注册]（SA控制起始）', 'feild': 'sacs_start_reg_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF初始注册成功率（CSCF控制起始）', 'feild': 'saccs_start_reg_init_succ_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': '5G+SA+IMS+CSCF注册成功率[含重注册]（CSCF控制起始）', 'feild': 'saccs_start_reg_suss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR语音话务量(Erl)', 'feild': 'vonr_voice_traffic', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR掉话率', 'feild': 'vonr_drop_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR用户面丢包率', 'feild': 'vonr_user_pkt_loss_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'VONR小区监控预警数据表-天', 'table': 'csem.f_nk_vonr_keykpi_cell_d', 'tableName': 'VONR小区监控预警数据表-天', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'VoNR接通率', 'feild': 'vonr_connect_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_5g_kpi_payload():
    """获取5G小区性能KPI报表payload"""
    print("[DEBUG-PAYLOAD] 生成 5G小区性能KPI报表 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '小时,天,周,月',
        'enodebField': 'gnodeb_id', 'cgiField': 'ncgi',
        'timeField': 'starttime', 'cellField': 'nrcell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '数据时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'NCGI', 'feild': 'ncgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'nrcell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '人力区县分公司', 'feild': 'branch', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'RRC连接平均数', 'feild': 'rrc_connmean', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'RRC连接最大数', 'feild': 'rrc_connmax', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'PDCP层上行业务字节数', 'feild': 'pdcp_up_tput_bytes', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'PDCP层下行业务字节数', 'feild': 'pdcp_down_tput_bytes', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PDCP层吞吐量-上行(Mbps)', 'feild': 'pdcp_up_tput_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PDCP层吞吐量-下行(Mbps)', 'feild': 'pdcp_down_tput_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PRB利用率-上行(%)', 'feild': 'prb_ul_util_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': '小区PRB利用率-下行(%)', 'feild': 'prb_dl_util_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'CQI=10占比(%)', 'feild': 'cqi10_rate', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': 'SA_CU性能', 'table': 'appdbv3.a_common_pm_sacu', 'tableName': '5GSA_CU性能报表', 'datatype': 'numeric', 'columntype': 1, 'feildName': 'PDSCHbler(%)', 'feild': 'pdsch_bler', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload


def get_4g_kpi_payload():
    """获取4G小区性能KPI报表payload"""
    print("[DEBUG-PAYLOAD] 生成 4G小区性能KPI报表 payload")
    payload = {
        'draw': 1, 'start': 0, 'length': 200, 'total': 0,
        'geographicdimension': '小区，网格，地市，分公司', 'timedimension': '小时,天,周.月,忙时,15分钟',
        'enodebField': 'enodeb_id', 'cgiField': 'cgi',
        'timeField': 'starttime', 'cellField': 'cell', 'cityField': 'city',
        'result': {'result': [
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '开始时间', 'feild': 'starttime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'timestamp', 'columntype': 1, 'feildName': '结束时间', 'feild': 'endtime', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'CGI', 'feild': 'cgi', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '小区名称', 'feild': 'cell_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属地市', 'feild': 'city', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '所属区县', 'feild': 'area', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网格', 'feild': 'grid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '责任田', 'feild': 'marketduty', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '市场网格', 'feild': 'marketgrid', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网络制式', 'feild': 'network_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '设备厂家', 'feild': 'vendor', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '覆盖类型', 'feild': 'cover_type', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '使用频段', 'feild': 'frequency_band', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '详细频段', 'feild': 'freq_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '频点', 'feild': 'earfcn', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'PCI', 'feild': 'pci', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': 'TAC', 'feild': 'tac', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '网元状态', 'feild': 'state', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
            {'feildtype': '公共信息（小区级粒度）', 'table': 'appdbv3.a_common_pm_lte', 'tableName': '4G小区性能KPI报表', 'datatype': 'character varying', 'columntype': 1, 'feildName': '基站名称', 'feild': 'enodeb_name', 'poly': '无', 'anyWay': '无', 'chart': '无', 'chartpoly': '无'},
        ], 'tableParams': {'supporteddimension': None, 'supportedtimedimension': ''}, 'columnname': ''},
        'where': [
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '>=', 'val': '2026-04-19 00:00:00', 'whereCon': 'and', 'query': True},
            {'datatype': 'timestamp', 'feild': 'starttime', 'feildName': '', 'symbol': '<', 'val': '2026-04-19 23:59:59', 'whereCon': 'and', 'query': True},
            {'datatype': 'character', 'feild': 'city', 'feildName': '', 'symbol': 'in', 'val': '阳江', 'whereCon': 'and', 'query': True}
        ],
        'indexcount': 0
    }
    return payload
