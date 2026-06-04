#ifndef EASYKNOB_CONFIG_H
#define EASYKNOB_CONFIG_H

#include <Arduino.h>

// ── Persistent config keys ─────────────────────────────────
#define EK_CFG_DAMPING          "damp"
#define EK_CFG_FORCE_THRESHOLD  "fthr"
#define EK_CFG_FEEDBACK_GAIN    "gain"
#define EK_CFG_ZERO_ANGLE       "zero"
#define EK_CFG_RANGE_HALF       "rng2"

// ── Defaults ───────────────────────────────────────────────
#define EK_DEFAULT_DAMPING         0
#define EK_DEFAULT_FORCE_THRESHOLD 50    // x100
#define EK_DEFAULT_FEEDBACK_GAIN   500   // x100
#define EK_DEFAULT_RANGE_HALF      314   // ~pi * 100

// ── API ────────────────────────────────────────────────────
void ek_cfg_init();
void ek_cfg_load();
void ek_cfg_save();
void ek_cfg_save_debounced();   // saves only if dirty & >3s since last save
void ek_cfg_mark_dirty();

// Accessors (read/write RAM cache, optionally persist)
uint8_t  ek_cfg_get_damping();
void     ek_cfg_set_damping(uint8_t val);        // 0-100

uint16_t ek_cfg_get_force_threshold();
void     ek_cfg_set_force_threshold(uint16_t val);

uint16_t ek_cfg_get_feedback_gain();
void     ek_cfg_set_feedback_gain(uint16_t val);

float    ek_cfg_get_zero_angle();
void     ek_cfg_set_zero_angle(float rad);

uint16_t ek_cfg_get_range_half();
void     ek_cfg_set_range_half(uint16_t val100);

#endif
