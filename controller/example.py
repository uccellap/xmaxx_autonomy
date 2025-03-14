import serial
import time
import threading
import struct
from struct import Struct

#-------------------------------------------
"""
// Defines
//----------------------------------------------------
// API
#define AUTONOMY_API_MAGIC         (0x5A5A5A5A)
#define AUTONOMY_API_VERSION       (0x01)
#define AUTONOMY_CMD_TYPE_DRIVE    (0x01)
#define AUTONOMY_DATA_TYPE_TELEM   (0x81)

// Types
//----------------------------------------------------
typedef struct __attribute__((packed)) {
    int16_t     throttle;       // 1000-1500-2000
    int16_t     steering;       // 1000-1500-2000
} AutonomyDriveCmd_t;

typedef struct __attribute__((packed)) {
    uint32_t    magic;
    uint8_t     version;
    uint8_t     type;
    uint8_t     crc;
    union {
        AutonomyDriveCmd_t drive;
    } msg;
} AutonomyCmd_t;

typedef struct __attribute__((packed)) {
    uint64_t    counter;
    uint8_t     state;
    uint16_t    rcThrottle;     // 1000-1500-2000
    uint16_t    rcSteering;
    uint16_t    rcSwitchA;
    uint16_t    rcSwitchB;
    uint16_t    rcSwitchC;
    uint16_t    rcSwitchD;
    uint16_t    acThrottle;
    uint16_t    acSteering;
    uint8_t     upRssi;
    uint8_t     upLqi;
    uint8_t     downRssi;
    uint8_t     downLqi;
    uint16_t    escVoltageRaw;
    uint16_t    escCurrentRaw;
    uint16_t    escRpmRaw;
    uint16_t    escTempRaw;
} AutonomyTelemetryData_t;


// note - these are close enough that we won't
// bother with variable length structs
typedef struct __attribute__((packed)) {
    uint32_t    magic;
    uint8_t     version;
    uint8_t     type;
    uint8_t     crc;
    union {
        AutonomyTelemetryData_t telem;
    } msg;
} AutonomyData_t;
"""

#-------------------------------------------
MsgHeader = Struct('<LBBB')
MsgTelem  = Struct('<QBHHHHHHHHBBBBHHHH')

MsgDrive  = Struct('<LBBBHH')

#-------------------------------------------
def crc8(data):
    c = 0
    for i in range(len(data)):
        c ^= data[i]
        for j in range(8):
            if(c & 0x80):
                c = ((c << 1) ^ (0x1e7))
            else:
                c = (c << 1)
    return c

#-------------------------------------------
def readThread(ser):
    sync = False

    try:
        while True:
            header = bytearray()
            if sync:
                header = ser.read(MsgHeader.size)
            else:
                message = ''
                while not sync:
                    b = ser.read(1)
                    if(b == b'Z'):
                        header.extend(b)
                        if(header == bytearray(b'ZZZZ')):
                            header.extend(ser.read(MsgHeader.size-4))
                            print("[-] MSG: ", message)
                            print("[-] Got sync...")
                            sync = True
                    else:
                        try:
                            message += b.decode()
                        except:
                            pass
                        header = bytearray()

            # unpack header
            msg = MsgHeader.unpack(header)
            msg_magic = msg[0]
            msg_version = msg[1]
            msg_type = msg[2]
            msg_crc = msg[3]

            if msg_magic != 0x5A5A5A5A:
                print("[!] Bad magic")
                sync = False
                continue

            if msg_version != 0x01:
                print("[!] Bad version")
                sync = False
                continue

            # read body
            # all messages are the size of the largest (union)
            body = bytearray()
            body.extend(ser.read(MsgTelem.size))

            # check CRC
            msg = MsgHeader.pack(msg_magic, msg_version, msg_type, 0)
            computed_crc = crc8(msg+body)

            if msg_crc != computed_crc:
                print("[!] Bad CRC")
                sync = False
                continue

            # telem
            if msg_type == 0x81:
                telemMsg = MsgTelem.unpack(body)
                print("[-] telem : {}".format(telemMsg))            


    except Exception as e1:
        print("[!] Error: " + str(e1))

#-------------------------------------------
def setupSerial():
    ser = serial.Serial()
    ser.port = "/dev/cu.usbserial-0001"
    ser.baudrate = 460800
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.timeout = None
    ser.xonxoff = False
    ser.rtscts = False
    ser.dsrdtr = False
    ser.writeTimeout = None

    try: 
        ser.open()
    except Exception as e:
        print("error opening serial port: " + str(e))
        return None

    return ser

def main():
    print("[-] XMAXX Interface Startup")
    ser = setupSerial()

    if ser is not None:
        rt = threading.Thread(target=readThread, args=(ser,))
        rt.start()

        while(True):
            time.sleep(1.0/30.0)
            
            """
            print("[-] Issuing test command...")
            msg = MsgDrive.pack(0x5A5A5A5A, 0x01, 0x01, 0x0, 1111, 2222)
            calculated_crc = crc8(msg)
            msg = MsgDrive.pack(0x5A5A5A5A, 0x01, 0x01, calculated_crc, 1111, 2222)
            ser.write(msg)
            ser.flush()"
            """
            
        rt.join()

    if ser:
        ser.close()
    return

if __name__ == '__main__':
    main()

