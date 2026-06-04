#ifndef EASYKNOB_PROTOCOL_H
#define EASYKNOB_PROTOCOL_H

#include <Arduino.h>

#define PROTO_SYNC1       0xAA
#define PROTO_SYNC2       0x55
#define CMD_REPORT        0x01
#define CMD_COMMAND       0x02
#define CMD_PING          0x03
#define CMD_ACK           0x10
#define MODE_IDLE         0
#define MODE_GRIPPER      1
#define MODE_CALIBRATE    2
#define FLAG_CALIBRATED   0x01
#define FLAG_FORCE_ACTIVE 0x02

struct ReportPacket {
    float    angle;
    float    raw_angle;
    float    velocity;
    float    torque_cmd;
    uint8_t  mode;
    uint8_t  status_flags;
};

struct CommandPacket {
    int16_t  force;
    uint16_t force_threshold;
    uint16_t feedback_gain;
    uint8_t  mode_cmd;
    uint8_t  damping;   // 0-100, scaled x1
};

void proto_init();
void proto_send_report(const ReportPacket* rpt);
bool proto_poll_command(CommandPacket* cmd);
uint16_t proto_crc16(const uint8_t* data, size_t len);

#endif
