#ifndef GRIPPER_CONTROL_H
#define GRIPPER_CONTROL_H

#include <Arduino.h>
#include "gripper_protocol.h"

typedef enum {
    GRIP_IDLE = 0,
    GRIP_ACTIVE,
    GRIP_CALIBRATE
} GripperMode;

extern GripperMode grip_mode;
extern float grip_zero_angle;
extern float grip_min_angle;
extern float grip_max_angle;
extern float grip_range_half;
extern float grip_torque_applied;

void gripper_init();
void gripper_set_mode(GripperMode m);
void gripper_calibrate_zero();
float gripper_normalize_angle(float raw_angle);
uint8_t gripper_get_force_active_flag();
void gripper_loop(const CommandPacket* cmd);
void gripper_update_rgb();

#endif
