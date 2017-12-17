#!/usr/bin/python
#  -*- coding: UTF-8 -*-
__author__ = 'minseok'
import sys
import requests
import json
import urllib
import HEADERS
import datetime
import re
import threading
reservation_option = {
    'HourStart': 10,
    'DurationHour': 7,
    'PersonCnt': '3',
    'try_less_time': True,
    'try_next_time': 2
}
login_info = {
    'id': ''
}
class Reservation:

    def __init__(self, option):
        self.reservation_option = option.copy()
        self._cookie = None
        self._room_status = {}
        self._cur_time = datetime.datetime.now()
        for i in range(23, 35):
            self._room_status[i] = {}
            for j in range(0, 24):
                if j < self._cur_time.hour:
                    self._room_status[i][j] = False
                elif j > 21:
                    self._room_status[i][j] = False
                else:
                    self._room_status[i][j] = True

    def login(self):
        encrypted = self.pw_encrypt_test()
        if encrypted is None:
            return
        param = {'user_id': login_info['id'], 'user_pw': encrypted}
        HEADERS.login_header['Content-Length'] = str(len(urllib.urlencode(param)))

        print "Try To login"
        try:
            r = requests.post('http://www.ggihub.or.kr/front/doLogin', params=param, headers=HEADERS.login_header)
        except Exception as e:
            print "Failed To login"
            print e
            return False
        print "Success To login"

        if r.status_code == 200:
            self._cookie = r.cookies
            #print r.cookies
            return True
        else:
            print r.content
            print r.status_code
            return False

    def pw_encrypt_test(self):
        param = {'passwd': login_info['pw']}
        print "Try To get Encrypted Password"
        try:
            r = requests.get('http://www.ggihub.or.kr/common/SeedEncryption', params=param, headers=HEADERS.encrypt_header)
            encrypted = json.loads(r.content)
        except Exception as e:
            print "Failed To get Encrypted Password"
            print e
            return None
        print "Success To get Encrypted Password"
        return encrypted['passwd']

    def get_available_time(self):
        param = {'RoomCode': '9', 'searchDate': '%d%02d%02d' % (self._cur_time.year, self._cur_time.month, self._cur_time.day)}
        HEADERS.available_time_header['Referer'] = 'http://www.ggihub.or.kr:8081/library/kiosk_pc.php?mode=all&sno='

        print "Try To get Reserve Info"

        try:
            r = requests.get('http://www.ggihub.or.kr:8081/library/getReserveInfo_Sql.php', params=param, headers=HEADERS.available_time_header, cookies=self._cookie if self._cookie else None)
            if r.status_code != 200:
                print "Failed To get Reserve Info"
                print r.status_code
                return False
            parsed = json.loads(r.content)
        except Exception as e:
            print "Failed To get Reserve Info"
            print e
            return False
        print "Success To get Reserve Info"

        for val in parsed:
            match = re.match('R([0-9]*)', val[u'SEAT_NAME'])
            if bool(match):
                room_id = int(match.groups()[0])
                start = int(val[u'LOG_START'])
                end = int(val[u'LOG_END'])
                for i in range(start, start + end):
                    self._room_status[room_id][i] = False

        return parsed

    def reserve(self):
        for start_time in range(self.reservation_option['HourStart'], self.reservation_option['HourStart'] + self.reservation_option['try_next_time']):
            for room_id in self._room_status:
                times = self._room_status[room_id]
                cnt = 0
                for j in range(start_time, 24):
                    if not times[j]:
                        break
                    cnt += 1

                if cnt >= self.reservation_option['DurationHour']:
                    if self._real_reserve(room_id, start_time, reservation_option['DurationHour']):
                        return True
        return False

    def _real_reserve(self, room_id, HourStart, DurationHour):
        if self._cookie is None:
            return False
        param = {
            'RoomName': 'R%d' % room_id,
            'RoomClass': 'project',
            'SeatCode': '%d' % (room_id - 22),
            'RoomCode': '9',
            'UserSNO': login_info['id'],
            'HourStart': str(HourStart),
            'DurationHour': str(DurationHour),
            'PersonCnt': self.reservation_option['PersonCnt']
        }
        HEADERS.reserve_header['Referer'] = 'http://www.ggihub.or.kr:8081/library/kiosk_pc.php?mode=all&sno=' + login_info['id']

        r = requests.post('http://www.ggihub.or.kr:8081/library/putReserve_Sql.php', params=param, headers=HEADERS.reserve_header, cookies = self._cookie)
        parsed = ''
        try:
            parsed = json.loads(r.content)
        except Exception as e:
            print "Failed To load"
            print r.content
            print e
            return False
        if parsed['result'] == '1' or parsed['result'] == 1:
            print "Success!"
            print parsed
            return True
        return False

    def retry(self):
        self.reservation_option['DurationHour'] -= 1
        if self.reservation_option['DurationHour'] == 0:
            return False
        return True

    def print_reservation_info(self):
        if self._cookie is None:
            return False
        param = {'RoomCode': '9', 'searchDate': '%d%02d%02d' % (self._cur_time.year, self._cur_time.month, self._cur_time.day)}
        HEADERS.available_time_header['Referer'] = 'http://www.ggihub.or.kr:8081/library/kiosk_pc.php?mode=all&sno=' + login_info['id']

        print "Try To get Reserve Info"

        try:
            r = requests.get('http://www.ggihub.or.kr:8081/library/getReserveInfo_Sql.php', params=param, headers=HEADERS.available_time_header, cookies=self._cookie)
            if r.status_code != 200:
                print "Failed To get Reserve Info"
                print r.status_code
                return False
            parsed = json.loads(r.content)
        except Exception as e:
            print "Failed To get Reserve Info"
            print e
            return False
        print "Success To get Reserve Info"
        print parsed

    def print_reservation_info2(self):
        result = self.get_available_time()
        for val in result:
            if val['LOG_USER_SNO'] == login_info['id']:
                print json.dumps(val, indent=2)
                return
            elif val['SEAT_NAME'] == 'R23':
                print json.dumps(val, indent=2)
        print "NO RESERVATION EXISTS!!"
        

def try_reservation():
    r = Reservation(reservation_option)
    retry = True
    if r.login():
        while retry:
            if r.get_available_time():
                if r.reserve():
                    return True
                else:
                    retry = reservation_option['try_less_time']
                    if not r.retry():
                        return True
    return False

def get_reservation():
    r = Reservation(reservation_option)
    r.print_reservation_info2()
def main(argv):
    get_reservation()


if __name__ == "__main__":
    main(sys.argv)
