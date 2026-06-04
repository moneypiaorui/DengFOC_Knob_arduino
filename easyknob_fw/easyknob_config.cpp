#include "easyknob_config.h"
#include <Preferences.h>

static Preferences ek_prefs;

// ── RAM cache ──────────────────────────────────────────────
static uint8_t  _damping         = EK_DEFAULT_DAMPING;
static uint16_t _force_threshold = EK_DEFAULT_FORCE_THRESHOLD;
static uint16_t _feedback_gain   = EK_DEFAULT_FEEDBACK_GAIN;
static float    _zero_angle      = 0.0f;
static uint16_t _range_half      = EK_DEFAULT_RANGE_HALF;

// ── Dirty tracking for debounced save ──────────────────────
static bool     _dirty       = false;
static uint32_t _last_save_ms = 0;
#define SAVE_DEBOUNCE_MS 3000

// ── Init ───────────────────────────────────────────────────
void ek_cfg_init() {
    ek_prefs.begin("easyknob", false);
}

// ── Load from NVS ──────────────────────────────────────────
void ek_cfg_load() {
    _damping         = ek_prefs.getUChar(EK_CFG_DAMPING,         EK_DEFAULT_DAMPING);
    _force_threshold = ek_prefs.getUShort(EK_CFG_FORCE_THRESHOLD, EK_DEFAULT_FORCE_THRESHOLD);
    _feedback_gain   = ek_prefs.getUShort(EK_CFG_FEEDBACK_GAIN,   EK_DEFAULT_FEEDBACK_GAIN);
    _zero_angle      = ek_prefs.getFloat(EK_CFG_ZERO_ANGLE,       0.0f);
    _range_half      = ek_prefs.getUShort(EK_CFG_RANGE_HALF,      EK_DEFAULT_RANGE_HALF);
}

// ── Save to NVS ────────────────────────────────────────────
void ek_cfg_save() {
    ek_prefs.putUChar(EK_CFG_DAMPING,         _damping);
    ek_prefs.putUShort(EK_CFG_FORCE_THRESHOLD, _force_threshold);
    ek_prefs.putUShort(EK_CFG_FEEDBACK_GAIN,   _feedback_gain);
    ek_prefs.putFloat(EK_CFG_ZERO_ANGLE,        _zero_angle);
    ek_prefs.putUShort(EK_CFG_RANGE_HALF,       _range_half);
    _dirty = false;
    _last_save_ms = millis();
}

// ── Debounced save ─────────────────────────────────────────
void ek_cfg_save_debounced() {
    if (_dirty && (millis() - _last_save_ms) > SAVE_DEBOUNCE_MS) {
        ek_cfg_save();
    }
}

void ek_cfg_mark_dirty() {
    _dirty = true;
}

// ── Accessors ──────────────────────────────────────────────
uint8_t ek_cfg_get_damping() { return _damping; }
void ek_cfg_set_damping(uint8_t val) {
    if (val != _damping) { _damping = val; _dirty = true; }
}

uint16_t ek_cfg_get_force_threshold() { return _force_threshold; }
void ek_cfg_set_force_threshold(uint16_t val) {
    if (val != _force_threshold) { _force_threshold = val; _dirty = true; }
}

uint16_t ek_cfg_get_feedback_gain() { return _feedback_gain; }
void ek_cfg_set_feedback_gain(uint16_t val) {
    if (val != _feedback_gain) { _feedback_gain = val; _dirty = true; }
}

float ek_cfg_get_zero_angle() { return _zero_angle; }
void ek_cfg_set_zero_angle(float rad) {
    _zero_angle = rad; _dirty = true;  // always save immediately on next cycle
}

uint16_t ek_cfg_get_range_half() { return _range_half; }
void ek_cfg_set_range_half(uint16_t val100) {
    if (val100 != _range_half) { _range_half = val100; _dirty = true; }
}
