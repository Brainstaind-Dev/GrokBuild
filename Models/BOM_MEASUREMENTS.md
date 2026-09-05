# BOM measurements (scaffold)

**Source list:** `Parts.md`  
**Units:** millimeters  
**Status:** Pi kit frozen from calipers (2026-08-11); other rows still open  

Measure the **as-built kit** (including headers, USB jacks, battery pouch, CanaKit packaging if Pi stays in a case).

| ID | Component | L | W | H | Notes / clearance needed |
|----|-----------|---|---|---|---------------------------|
| pi5 | Pi 5 board only | 85 | 56 | 17 | Official approx; prefer kit envelope |
| pi5_kit | CanaKit case + fan (as built) | **93.77** | **63.02** | **30.45** | Calipers 2026-08-11; fan included in H. Photo: `Models/PIinBod1.jpeg` |
| pi5_kit_open | CanaKit **base + board, fan lid OFF** | **93.77** | **63.02** | **~19** (opening depth) | Lid-off. GPIO on open face. USB-C+HDMI long wall; ETH/USB short; SD other short. Photos `Cana1`–`Cana9`. |
| canakit_fan | CanaKit 30 mm fan | **30** | **30** | **7.38** | Lead **63.92 mm**. Body-mounted on inner back; not on lid. |
| esp32 | ESP32-WROOM dev board | 55 | 28 | 13 | USB end open for flash |
| max9814 | Mic AGC board | | | | Ear recess; ×2 |
| spk_3w | Speaker 3 W 8 Ω | | | | Grill Ø; ×4 available |
| max98357 | I2S amp | | | | Near speaker bay |
| sg90 | Servo body | 23 | 12 | 29 | + horn disk clearance |
| vibe | Vibration motor | | | | Cup depth |
| mpu6050 | GY-521 module | | | | I2C pocket |
| fsr402 | FSR active area | 12.7 | — | thin | 0.5" circle; cable channel |
| rtc | DS3231 Waveshare | | | | Stack height |
| dht22 | DHT22 module | | | | Airflow hole |
| lipo_2k | 3.7 V 2000 mAh pouch | | | | Soft pack; no crush |
| tp4056 | Type-C charge module | | | | Panel mount access |
| gsr | Grove GSR | | | | External straps |
| max30102 | HR/SpO2 | | | | Finger clip interface |

## Assembly clearances (targets)

| Feature | Target (mm) |
|---------|-------------|
| Wall thickness (structural) | 1.6–2.0 |
| Pi kit airflow (fan face free) | ≥ 4 mm clear in front of fan; rear vent preferred |
| Charge / power exit | **Right side near torso base** (user 2026-08-11) |
| Pi airflow gap above SoC/area | ≥ 8 (bare board); kit uses top fan |
| Neck cable trunk ID | ≥ 12–15 |
| Screw insert (M3) | per insert datasheet |
| Mic port acoustic opening | ≥ board hole; foam optional later |
| Ear cup / pinna outer depth | design feature — measure fit with board behind |
| Latch arm thickness / length | design per joint; print for layer strength |

## Print envelope (P2S)

| Limit | Value |
|-------|--------|
| Printer build volume | 256 × 256 × 256 |
| Design max per stage | **250 × 250 × 250** (margin) |

## Measurement checklist

- [x] Pi 5 full CanaKit envelope (93.77 × 63.02 × 30.45) — 2026-08-11  
- [ ] Pi 5 board-only (optional)  
- [ ] One ESP32 board  
- [ ] Both MAX9814 boards  
- [ ] One speaker + one amp  
- [ ] One LiPo pack + one TP4056  
- [ ] One SG90  
- [ ] One MPU-6050  
- [ ] One FSR402  

Date measured: __________  
Measured by: __________
