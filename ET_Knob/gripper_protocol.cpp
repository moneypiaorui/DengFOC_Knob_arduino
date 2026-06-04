#include "gripper_protocol.h"

uint16_t proto_crc16(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc = (crc << 1);
        }
    }
    return crc;
}

static uint8_t tx_seq = 0;

void proto_init() {
    tx_seq = 0;
}

void proto_send_report(const ReportPacket* rpt) {
    uint8_t buf[32];
    uint8_t plen = 18;
    buf[0] = PROTO_SYNC1;
    buf[1] = PROTO_SYNC2;
    buf[2] = plen;
    buf[3] = tx_seq++;
    buf[4] = CMD_REPORT;
    memcpy(&buf[5], rpt, plen);
    uint16_t crc = proto_crc16(&buf[5], plen);
    buf[5 + plen]     = crc & 0xFF;
    buf[5 + plen + 1] = crc >> 8;
    Serial.write(buf, plen + 7);
}

enum RxState { WAIT_SYNC1, WAIT_SYNC2, WAIT_LEN, WAIT_SEQ,
               WAIT_CMD, WAIT_PAYLOAD, WAIT_CRC_LO, WAIT_CRC_HI };

static RxState  rx_st = WAIT_SYNC1;
static uint8_t  rx_buf[64];
static uint8_t  rx_plen = 0;
static uint8_t  rx_cmd = 0;
static uint8_t  rx_pos = 0;
static uint8_t  rx_crc_lo = 0;
static uint32_t rx_last_ms = 0;

static void rx_reset() {
    rx_st = WAIT_SYNC1;
    rx_pos = 0;
}

bool proto_poll_command(CommandPacket* cmd) {
    uint32_t now = millis();

    while (Serial.available() > 0) {
        uint8_t b = Serial.read();
        rx_last_ms = now;

        switch (rx_st) {
        case WAIT_SYNC1:
            if (b == PROTO_SYNC1) rx_st = WAIT_SYNC2;
            break;
        case WAIT_SYNC2:
            if (b == PROTO_SYNC2) rx_st = WAIT_LEN;
            else if (b != PROTO_SYNC1) rx_st = WAIT_SYNC1;
            break;
        case WAIT_LEN:
            if (b > 32) { rx_reset(); break; }
            rx_plen = b; rx_st = WAIT_SEQ; break;
        case WAIT_SEQ:
            rx_st = WAIT_CMD; break;
        case WAIT_CMD:
            rx_cmd = b; rx_pos = 0;
            rx_st = (rx_plen > 0) ? WAIT_PAYLOAD : WAIT_CRC_LO;
            break;
        case WAIT_PAYLOAD:
            if (rx_pos < sizeof(rx_buf)) rx_buf[rx_pos++] = b;
            if (rx_pos >= rx_plen) rx_st = WAIT_CRC_LO;
            break;
        case WAIT_CRC_LO:
            rx_crc_lo = b; rx_st = WAIT_CRC_HI; break;
        case WAIT_CRC_HI: {
            uint16_t rx_crc = rx_crc_lo | ((uint16_t)b << 8);
            uint16_t calc = proto_crc16(rx_buf, rx_plen);
            rx_reset();
            if (rx_crc == calc && rx_cmd == CMD_COMMAND && rx_plen == 7) {
                cmd->force           = (int16_t)(rx_buf[0] | (rx_buf[1] << 8));
                cmd->force_threshold = (uint16_t)(rx_buf[2] | (rx_buf[3] << 8));
                cmd->feedback_gain   = (uint16_t)(rx_buf[4] | (rx_buf[5] << 8));
                cmd->mode_cmd        = rx_buf[6];
                return true;
            }
            break;
        }
        }
    }

    if (rx_st != WAIT_SYNC1 && (millis() - rx_last_ms) > 100)
        rx_reset();

    return false;
}
