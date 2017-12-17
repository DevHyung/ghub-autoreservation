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
import time

# HourStart : reservation start time (0~22)
# DurationHour : Default Duration Time
# PersonCnt : Reservation Person Count
# try_less_time : if all reservation failed, try -1 Duration Time
# try_next_time : if all reservation failed in this start time, try +1 start time
#                   e.g.) tnt:2, start_time : 14~16 (Default + 2)
reservation_option = {
    'HourStart': 10,
    'DurationHour': 10,
    'PersonCnt': '3',
    'try_less_time': True,
    'try_next_time': 2
}
login_info = {
    'id': 'nawook96',
    'pw': 'as0331'
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

        for val in parsed:
            match = re.match('R([0-9]*)', val[u'SEAT_NAME'])
            if bool(match):
                room_id = int(match.groups()[0])
                start = int(val[u'LOG_START'])
                end = int(val[u'LOG_END'])
                for i in range(start, start + end):
                    self._room_status[room_id][i] = False

        return True

    def reserve(self):
        for start_time in range(self.reservation_option['HourStart'], self.reservation_option['HourStart'] + self.reservation_option['try_next_time']):
            #for room_id in self._room_status:
            #23. 25. 26. 29. 30. 33 list sequence reserve go
            list = [26, 29, 30, 25, 23]
            print "테스트접근"
            for test_id in list:
                times = self._room_status[test_id]
                cnt = 0
                for j in range(start_time, 24):
                    if not times[j]:
                        break
                    cnt += 1

                if cnt >= self.reservation_option['DurationHour']:
                    if self._real_reserve(test_id, start_time, reservation_option['DurationHour']):
                        return True

            print "테스트접근2"
            for room_id in range(23, 35):
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
            print "Room Number : R", room_id
            print parsed
            return True
        return False

    def retry(self):
        self.reservation_option['DurationHour'] -= 1
        if self.reservation_option['DurationHour'] == 0:
            return False
        return True

def try_reservation():
    r = Reservation(reservation_option)
    retry = True
    if r.login():
        #rogin cookie have
        waittime = datetime.datetime.now()
        wait = True
        # print curTime.hour
        while wait:
            waittime = datetime.datetime.now()
            # 6:00 start
            if waittime.hour == 6 and waittime.minute == 0:
                wait = False
            else:
                print "대기중", waittime
                threading._sleep(1)

        while retry:
            if r.get_available_time():
                if r.reserve():
                    return True
                else:
                    retry = reservation_option['try_less_time']
                    if not r.retry():
                        return True
    return False

def main(argv):
    #end try value false change ! and
    #end_try = True
    end_try = False
    print "gogo !"
    while True:
        threading._sleep(1)
        curTime = datetime.datetime.now()
        #print curTime.hour
        #if your start 6:00  below start 5:59
        if (curTime.hour == 5 and curTime.minute == 59 ) or ( curTime.hour == 6 and curTime.minute == 0 ) and not end_try:
            print "Try Time : ", curTime
            end_try = try_reservation()
            threading._sleep(5)
       # if curTime.hour == 5 and curTime.minute == 59:
            #end_try = False
        #print "Trying Reset! try date is %d%02d%02d" % (curTime.year, curTime.month, curTime.day)
        #print curTime


if __name__ == "__main__":
    main(sys.argv)
