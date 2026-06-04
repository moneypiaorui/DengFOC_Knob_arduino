#include "gripper_control.h"
#include "DengFOC.h"
#include "DFOC_RGB.h"

extern DFOC_RGB RGB;

GripperMode grip_mode           = GRIP_IDLE;
float       grip_zero_angle     = 0.0f;
float       grip_min_angle      = -3.1416f;
float       grip_max_angle      = 3.1416f;
float       grip_range_half     = 3.1416f;
float       grip_torque_applied = 0.0f;

static float cmd_force           = 0.0f;
static float cmd_force_threshold = 0.5f;
static float cmd_feedback_gain   = 5.0f;
static uint32_t rgb_last_ms = 0;
static uint8_t  rgb_bright = 0;
static int      rgb_dir = 1;

void gripper_init() {
    grip_mode = GRIP_IDLE;
    grip_zero_angle = 0.0f;
}

void gripper_set_mode(GripperMode m) {
    grip_mode = m;
}

void gripper_calibrate_zero() {
    grip_zero_angle = DFOC_M0_Angle();
    grip_min_angle  = grip_zero_angle - grip_range_half;
    grip_max_angle  = grip_zero_angle + grip_range_half;
    grip_mode = GRIP_ACTIVE;
}

float gripper_normalize_angle(float raw) {
    float diff = raw - grip_zero_angle;
    while (diff > grip_range_half)  diff -= 2.0f * grip_range_half;
    while (diff < -grip_range_half) diff += 2.0f * grip_range_half;
    return constrain((diff + grip_range_half) / (2.0f * grip_range_half), 0.0f, 1.0f);
}

uint8_t gripper_get_force_active_flag() {
    return (fabsf(cmd_force) >= cmd_force_threshold) ? FLAG_FORCE_ACTIVE : 0x00;
}

void gripper_loop(const CommandPacket* cmd) {
    float raw = DFOC_M0_Angle();
    float vel = DFOC_M0_Velocity();

    if (cmd) {
        cmd_force           = cmd->force / 100.0f;
        cmd_force_threshold = cmd->force_threshold / 100.0f;
        cmd_feedback_gain   = cmd->feedback_gain / 100.0f;
        switch (cmd->mode_cmd) {
        case 1: grip_mode = GRIP_ACTIVE; break;
        case 2: gripper_calibrate_zero(); break;
        case 3: grip_mode = GRIP_IDLE; break;
        }
    }

    switch (grip_mode) {
    case GRIP_IDLE:
        grip_torque_applied = -0.3f * vel;
        break;
    case GRIP_CALIBRATE:
        DFOC_M0_set_Force_Angle(grip_zero_angle);
        grip_torque_applied = 0.0f;
        return;
    case GRIP_ACTIVE:
        if (fabsf(cmd_force) < cmd_force_threshold) {
            grip_torque_applied = -0.5f * vel;
        } else {
            grip_torque_applied = constrain(-cmd_feedback_gain * cmd_force, -6.0f, 6.0f);
        }
        break;
    }

    DFOC_M0_setTorque(grip_torque_applied);
}

void gripper_update_rgb() {
    uint32_t now = millis();
    if (now - rgb_last_ms < 30) return;
    rgb_last_ms = now;

    uint8_t r = 0, g = 0, b = 0;
    switch (grip_mode) {
    case GRIP_IDLE:
        rgb_bright = constrain(rgb_bright + rgb_dir * 3, 0, 100);
        if (rgb_bright == 0 || rgb_bright == 100) rgb_dir = -rgb_dir;
        b = rgb_bright; break;
    case GRIP_ACTIVE:
        if (fabsf(cmd_force) >= cmd_force_threshold) {
            g = 10;
            r = constrain((int)(fabsf(cmd_force) * 20), 0, 255);
        } else { g = 128; }
        break;
    case GRIP_CALIBRATE:
        r = ((now / 200) % 2) ? 200 : 0;
        g = ((now / 200) % 2) ? 160 : 0;
        break;
    }
    RGB.setColor(0, r, g, b);
    RGB.show();
}
