#include "motor_function.h"
#include "OneButton.h"
#include "DFOC_RGB.h"
#include "DengFOC.h"
#include "gripper_control.h"

OneButton button(BUTTON1, true, true);
DFOC_RGB   RGB = DFOC_RGB();

void RGB_init() {
    RGB.begin();
}

void attachClick() {
    if (grip_mode == GRIP_IDLE)
        gripper_set_mode(GRIP_ACTIVE);
    else
        gripper_set_mode(GRIP_IDLE);
}

void attachDoubleClick() {
    gripper_calibrate_zero();
}

void attachLongPressStart() {}
void attachLongPressStop() {}
void attachDuringLongPress() {}
void attachMultiClick() {}

void button_event_init() {
    button.attachClick(attachClick);
    button.attachDoubleClick(attachDoubleClick);
    button.attachLongPressStart(attachLongPressStart);
    button.attachLongPressStop(attachLongPressStop);
    button.attachDuringLongPress(attachDuringLongPress);
    button.attachMultiClick(attachMultiClick);
    button.setPressTicks(600);
}

void button_attach_loop() {
    button.tick();
}

void button_vibrate() {
    static uint32_t last_vib = 0;
    static uint8_t  vib_st = 0;
    static uint32_t vib_start = 0;

    switch (vib_st) {
    case 0:
        if (digitalRead(BUTTON1) == LOW && millis() - last_vib > 800) {
            last_vib = millis();
            vib_st = 1;
            vib_start = millis();
        }
        break;
    case 1:
        DFOC_M0_setTorque(0.3f);
        if (millis() - vib_start > 3) vib_st = 2;
        break;
    case 2:
        DFOC_M0_setTorque(-0.3f);
        if (millis() - vib_start > 6) vib_st = 0;
        break;
    }
}

void knob_init() {
    pinMode(BUTTON1, INPUT_PULLUP);
}
