"""Đổi lịch âm Việt Nam (múi giờ +7) sang dương lịch — thuật toán thiên văn của Hồ Ngọc Đức (dùng phổ biến cho
lịch Việt). Chỉ dùng để TÍNH ngày lễ theo luật (Tết Nguyên đán, Giỗ Tổ Hùng Vương); không phải số liệu nhập tay.
"""
from __future__ import annotations

import math
from datetime import date

TZ = 7.0


def _jd(d: int, m: int, y: int) -> int:
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    jd = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045
    if jd < 2299161:
        jd = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - 32083
    return jd


def _jd_sang_ngay(jd: int) -> date:
    if jd > 2299160:
        a = jd + 32044
        b = (4 * a + 3) // 146097
        c = a - (b * 146097) // 4
    else:
        b = 0
        c = jd + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    return date(b * 100 + d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1)


def _trang_moi(k: int) -> int:
    T = k / 1236.85
    T2, T3 = T * T, T * T * T
    dr = math.pi / 180
    Jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    Jd1 += 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
    C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr) + 0.0021 * math.sin(2 * dr * M)
    C1 = C1 - 0.4068 * math.sin(Mpr * dr) + 0.0161 * math.sin(dr * 2 * Mpr)
    C1 = C1 - 0.0004 * math.sin(dr * 3 * Mpr)
    C1 = C1 + 0.0104 * math.sin(dr * 2 * F) - 0.0051 * math.sin(dr * (M + Mpr))
    C1 = C1 - 0.0074 * math.sin(dr * (M - Mpr)) + 0.0004 * math.sin(dr * (2 * F + M))
    C1 = C1 - 0.0004 * math.sin(dr * (2 * F - M)) - 0.0006 * math.sin(dr * (2 * F + Mpr))
    C1 = C1 + 0.0010 * math.sin(dr * (2 * F - Mpr)) + 0.0005 * math.sin(dr * (2 * Mpr + M))
    if T < -11:
        dt = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
    else:
        dt = -0.000278 + 0.000265 * T + 0.000262 * T2
    return int(Jd1 + C1 - dt + 0.5 + TZ / 24)


def _kinh_do_mt(jdn: int) -> int:
    T = (jdn - 2451545.5 - TZ / 24) / 36525
    T2 = T * T
    dr = math.pi / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    DL = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M) + 0.000290 * math.sin(dr * 3 * M)
    L = (L0 + DL) * dr
    L = L - math.pi * 2 * int(L / (math.pi * 2))
    return int(L / math.pi * 6)


def _thang11(y: int) -> int:
    off = _jd(31, 12, y) - 2415021
    k = int(off / 29.530588853)
    nm = _trang_moi(k)
    if _kinh_do_mt(nm) >= 9:
        nm = _trang_moi(k - 1)
    return nm


def _nhuan(a11: int) -> int:
    k = int((a11 - 2415021.076998695) / 29.530588853 + 0.5)
    i, arc = 1, _kinh_do_mt(_trang_moi(k + 1))
    while True:
        last = arc
        i += 1
        arc = _kinh_do_mt(_trang_moi(k + i))
        if not (arc != last and i < 14):
            break
    return i - 1


def am_sang_duong(ngay: int, thang: int, nam: int, nhuan: bool = False) -> date:
    """Ngày âm (ngay/thang/nam âm) → ngày dương."""
    if thang < 11:
        a11, b11 = _thang11(nam - 1), _thang11(nam)
    else:
        a11, b11 = _thang11(nam), _thang11(nam + 1)
    k = int(0.5 + (a11 - 2415021.076998695) / 29.530588853)
    off = thang - 11
    if off < 0:
        off += 12
    if b11 - a11 > 365:
        lo = _nhuan(a11)
        lm = lo - 2
        if lm < 0:
            lm += 12
        if nhuan and thang != lm:
            raise ValueError("Tháng nhuận không đúng")
        if nhuan or off >= lo:
            off += 1
    return _jd_sang_ngay(_trang_moi(k + off) + ngay - 1)
