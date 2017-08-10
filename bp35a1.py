import sys
from logging import getLogger, NullHandler

import serial

logger = getLogger(__name__)
logger.addHandler(NullHandler())


def parse_echonet_lite_frame(frame_str):
    dic = {}
    dic["EHD1"] = frame_str[:2]
    dic["EHD2"] = frame_str[2:4]
    dic["TID"] = frame_str[4:8]
    dic["SEOJ"] = frame_str[8:14]
    dic["DEOJ"] = frame_str[14:20]
    dic["ESV"] = frame_str[20:22]
    dic["OPC"] = frame_str[22:24]
    prop_num = int(dic["OPC"], 16)
    dic["PROPS"] = []
    idx = 24
    for i in range(prop_num):
        prop = {}
        prop["EPC"] = frame_str[idx:idx + 2]
        prop["PDC"] = frame_str[idx + 2:idx + 4]
        data_len = int(prop["PDC"], 16)
        prop["EDT"] = frame_str[idx + 4:idx + 4 + data_len * 2]
        idx += 4 + data_len * 2
        dic["PROPS"].append(prop)
    return dic


class BRouteReader:
    def __init__(self, serial_dev_name):
        self.ser = serial.Serial(serial_dev_name, 115200, timeout=1)
        self.ipv6 = ""

    def connect(self, b_route_id, b_route_password):
        self.ser.write("SKVER\r\n".encode())
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break

        self.ser.write("SKINFO\r\n".encode())
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break

        # set id / pass
        self.ser.write(("SKSETRBID " + b_route_id + "\r\n").encode())
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break
        self.ser.write(("SKSETPWD C " + b_route_password + "\r\n").encode())
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break

        pan_info = {}
        remaining_time = 30
        scan_completed = False
        while True:
            if not scan_completed:
                self.ser.write("SKSCAN 2 FFFFFFFF 4\r\n".encode())
                scan_completed = True
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                remaining_time -= 1

            if response.startswith("EVENT 22"):
                scan_completed = False
                if "Channel" in pan_info and "Pan ID" in pan_info and "Addr" in pan_info:
                    break
            elif response.startswith("  "):
                pan_res = response.strip().split(":")
                pan_info[pan_res[0]] = pan_res[1]

            if remaining_time == 0:
                raise TimeoutError

        self.ser.write(("SKSREG S2 " + pan_info["Channel"] + "\r\n").encode())
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break

        self.ser.write(("SKSREG S3 " + pan_info["Pan ID"] + "\r\n").encode())
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break

        ipv6_lower = ":".join(
            [pan_info["Addr"][2:4], pan_info["Addr"][4:8], pan_info["Addr"][8:12], pan_info["Addr"][12:16]])
        self.ipv6 = "FE80:0000:0000:0000:02" + ipv6_lower
        self.ser.write(("SKJOIN " + self.ipv6 + "\r\n").encode())
        remaining_time = 30
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                remaining_time -= 1
            if response.startswith("EVENT 25"):
                break
            if remaining_time == 0:
                raise TimeoutError

    def read_moment_power_consumption(self, timeout_sec=20):
        resp = parse_echonet_lite_frame(self.read(0xE7, timeout_sec=timeout_sec))
        return int(resp["PROPS"][0]["EDT"], 16)

    def read(self, epc, timeout_sec=20):
        frame = b"\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x62\x01" + epc.to_bytes(1, "big") + b"\x00"
        command = "SKSENDTO 1 {0} 0E1A 1 {1:04X} ".format(self.ipv6, len(frame))
        self.ser.write(command.encode() + frame)
        remaining_time = timeout_sec
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                remaining_time -= 1

            if response.startswith("ERXUDP"):
                splitted = response.split()
                frame = splitted[8]
                seoj = frame[8:8 + 6]
                esv = frame[20:20 + 2]
                epc = frame[24:24 + 2]
                if seoj == "028801" and esv == "72":
                    return frame
            if remaining_time == 0:
                raise TimeoutError

    def write(self, epc, data_to_write_as_bytes):
        frame = b"\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x60\x01"
        frame += epc.to_bytes(1, "big")
        frame += len(data_to_write_as_bytes).to_bytes(1, "big")
        frame += data_to_write_as_bytes

        command = "SKSENDTO 1 {0} 0E1A 1 {1:04X} ".format(self.ipv6, len(frame))
        self.ser.write(command.encode() + frame)
        while True:
            response = self.ser.readline().decode()
            if response:
                logger.debug("Response:" + response[:-2])
            else:
                raise TimeoutError
            if response == "OK\r\n":
                break
