#ifndef MOTOR_FUNCTION_H
#define MOTOR_FUNCTION_H

#include <Arduino.h>

#define BUTTON1  4
#define BUTTON2 -1
#define BUTTON3 -1

void attachClick();
void attachDoubleClick();
void attachLongPressStart();
void attachLongPressStop();
void attachDuringLongPress();
void attachMultiClick();
void button_event_init();
void button_attach_loop();
void button_vibrate();
void knob_init();
void RGB_init();

#endif
