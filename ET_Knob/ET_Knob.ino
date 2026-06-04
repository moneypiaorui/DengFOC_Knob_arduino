// ET_Knob - Force Feedback Gripper Controller
// USB Serial binary protocol, 921600 baud, 100Hz

#include "DengFOC.h"
#include "DFOC_RGB.h"
#include "motor_function.h"
#include "gripper_protocol.h"
#include "gripper_control.h"

int Sensor_DIR = 1;
int Motor_PP   = 7;

// Globals for DFOC_RGB blink compatibility
int state          = 0;
int last_state_RGB = 0;

#define REPORT_INTERVAL_US 10000

static uint32_t last_report_us = 0;

void setup() {
    Serial.begin(921600);

    pinMode(12, OUTPUT);
    digitalWrite(12, HIGH);

    DFOC_Vbus(12.6);
    DFOC_alignSensor(Motor_PP, Sensor_DIR);

    RGB_init();
    button_event_init();
    knob_init();
    proto_init();
    gripper_init();

    DFOC_M0_SET_ANGLE_PID(0.2, 0, 0.0005, 100000, 5);
    last_report_us = micros();
}

void loop() {
    runFOC();
    button_attach_loop();
    button_vibrate();

    CommandPacket cmd;
    gripper_loop(proto_poll_command(&cmd) ? &cmd : NULL);

    uint32_t now = micros();
    if (now - last_report_us >= REPORT_INTERVAL_US) {
        last_report_us = now;
        float raw = DFOC_M0_Angle();
        ReportPacket rpt;
        rpt.angle       = gripper_normalize_angle(raw);
        rpt.raw_angle   = raw;
        rpt.velocity    = DFOC_M0_Velocity();
        rpt.torque_cmd  = grip_torque_applied;
        rpt.mode        = (uint8_t)grip_mode;
        rpt.status_flags = FLAG_CALIBRATED | gripper_get_force_active_flag();
        proto_send_report(&rpt);
    }

    gripper_update_rgb();
}
