# Справочник по приборам — MA2 Profiles

Последнее обновление: 2026-06-24

---

## Содержание MA2 профилей

```
MA2_Profiles/
├── IL-ENERGY/
│   ├── iLighting@IL-ENERGY_Wash_19_HC@18ch.xml
│   ├── iLighting@IL-ENERGY_Wash_19_HC@26ch.xml
│   ├── iLighting@IL-ENERGY_Wash_19_HC@38ch.xml
│   └── iLighting@IL-ENERGY_Wash_19_HC@76ch_pixel.xml
└── LightSky/
    ├── light_sky@aquapearl_pro_ii@26ch.xml
    ├── light_sky@aquapearl_pro_ii@35ch.xml
    ├── light_sky@aquapearl_pro_ii@98ch_pixel.xml
    ├── light_sky@super_scope_color@35ch@60ch.xml    ← 2 режима в одном файле
    ├── light_sky@super_scope_ii@42ch@54ch.xml
    ├── light_sky@super_scope_pro@33ch@36ch.xml
    └── light_sky@super_scope_plus@43ch@55ch.xml
```

Установка: скопировать XML в `%appdata%\MA Lighting Technologies\grandma\gma2_V_X.X.X\library\`  
(или на USB `/gma2/library/`)

---

## 1. IL-ENERGY Wash 19 HC

**Тип**: LED Moving Head Wash (IP-rated)  
**Производитель**: iLighting (российская марка, ОЕМ = ProLights Astra Wash19Pix)  
**Источник света**: 19 × 40W RGB + WW LED (High CRI)  
**Зум**: 5°–45°  
**Pan/Tilt**: 540° / 218°  
**Мощность**: 730W  
**IP**: IP66  
**Особенности**: iCC Color Calibration, вращающийся фронтальный рассеиватель, управляемое LED кольцо

### DMX режимы

| Режим | Каналы | Назначение |
|-------|--------|-----------|
| Basic | 18CH | Базовый: Pan/Tilt, Dim, Shutter, RGBW, Macro, CTO, Zoom, Pixel XF |
| Standard | 26CH | +Fine каналы RGBW, Zoom Fine, W-to-Color XF, CTO на цвет, Tint |
| Extended | 38CH | +Pattern/Speed/Fade/Transition, FG/BG Intensity/Strobe, BG RGBW |
| Pixel | 76CH | 18 базовых + 19 пикселей × RGBW (57CH) + LED кольцо (1CH) |

### Ключевые DMX каналы (18CH базовый)

| Ch | Функция |
|----|---------|
| 1+2 | PAN 16-bit |
| 3+4 | TILT 16-bit |
| 5 | P/T Speed |
| 6+7 | DIM 16-bit |
| 8 | SHUTTER/Strobe |
| 9 | Color Macro |
| 10 | CTO |
| 11 | ZOOM |
| 12 | Pixel Crossfade |
| 13 | CTRL |
| 14 | RESET |
| 15 | R |
| 16 | G |
| 17 | B |
| 18 | W (Warm White) |

### Аналог / OEM источник

**ProLights Astra Wash19Pix** (итальянский бренд, Music & Lights S.r.l.) — идентичная DMX архитектура. Тот же OEM завод. Для ProLights есть официальные MA2 профили на prolights.it.

---

## 2. Aquapearl-Pro II

**Тип**: LED Moving Head Wash, IP66  
**Производитель**: Light Sky (Fly Dragon Lighting Equipment Co., Ltd)  
**Источник света**: 19 × 40W RGBW LED  
**Зум**: 5°–25° beam / 7°–45° zoom  
**Pan/Tilt**: 540° / 218°  
**Мощность**: 730W  
**IP**: IP66  
**Особенности**: iCC Color Calibration, вращающийся фронтальный объектив, управляемое LED кольцо

### DMX режимы

| Режим | Каналы | Назначение |
|-------|--------|-----------|
| Standard | 26CH | Базовый с кольцом |
| Special | 35CH | RGBW-first order, расширенные эффекты |
| Pixel | 98CH | Полный пиксельный контроль |

### Структура 26CH

| Ch | Функция |
|----|---------|
| 1+2 | PAN 16-bit |
| 3+4 | TILT 16-bit |
| 5 | CTRL |
| 6 | ZOOM |
| 7 | ZOOM_ROT (вращение фронтальной линзы) |
| 8+9 | DIM 16-bit |
| 10 | SHUTTER |
| 11 | MACRO/CW1 |
| 12 | CCT/CTO |
| 13 | Static Effect |
| 14 | Dynamic Effect |
| 15 | Effect Speed |
| 16 | Effect Delay |
| 17 | BG Color |
| 18 | BG Dim |
| 19 | R |
| 20 | G |
| 21 | B |
| 22 | W |
| 23 | Ring Dim |
| 24 | Ring Macro |
| 25 | Ring Effect |
| 26 | Ring Speed |

### Отличие от IL-ENERGY Wash 19 HC

Оба прибора: 19 × 40W RGBW, IP66, 540°/218°, iCC. Разница:
- Aquapearl-Pro II: Light Sky, RGBW (без High CRI), вращающийся объектив
- IL-ENERGY: iLighting/ProLights OEM, RGB+WW High CRI, нет вращения объектива
- DMX структура разная

---

## 3. Super Scope Color

**Тип**: 4-in-1 LED Moving Head Profile Spot  
**Производитель**: Light Sky  
**Источник света**: 600W RGBAL (5-цветный) LED модуль  
**Световой поток**: 17600 Lm | **Освещённость**: 12500 lux @ 10m  
**Зум**: 5.9°–52° | **Линза**: 180mm  
**Pan/Tilt**: 540° / 270°  
**Мощность**: 1050W | **IP**: IP20  
**Цветовая система**: iCC™ + 165 электронных цветовых чипов + Virtual CMY + Virtual CTO  
**CRI**: Ra ≥ 95, R9 ≥ 95, TLCI ≥ 95  
**Температура**: 2700–8000K

### DMX режимы

| Режим | Каналы | Назначение |
|-------|--------|-----------|
| Standard | 35CH | Основной: CMY + гобо + фрейминг |
| Full | 60CH | 16-bit CMY/Iris/Zoom/Focus, freq control |
| Extended+ | 64CH | RGB A L раздельно 16-bit |
| Compatible | 49CH | Упрощённый с virtual CW |

### Ключевые DMX каналы (35CH)

| Ch | Функция | MA2 атрибут |
|----|---------|-------------|
| 1+2 | PAN 16-bit | PAN |
| 3+4 | TILT 16-bit | TILT |
| 5 | Speed | PTSPEED |
| 6 | Functions/Ctrl | DUMMY |
| 7 | Colour Functions | DUMMY |
| 8 | Virtual Colour Wheel (165 гелей) | CW1 |
| 9 | Cyan (Red) | CYAN |
| 10 | Magenta (Green) | MAGENTA |
| 11 | Yellow (Blue) | YELLOW |
| 12 | CTC (2700–8000K) | CTO |
| 13 | Effect Wheel | EFFECTS |
| 14 | Effect Rotation | EFFECTS |
| 15 | Gobo Wheel 1 (7 гобо) | GOBO1 |
| 16 | Gobo 1 Rotation | GOBO1POS |
| 17 | Gobo Wheel 2 (7 гобо) | GOBO2 |
| 18 | Gobo 2 Rotation | GOBO2POS |
| 19 | Prism (8-facet) | PRISM1 |
| 20 | Prism Rotation | EFFECTS |
| 21 | Frost (light+medium+heavy) | FROST1 |
| 22 | Iris (5–100%) | IRIS |
| 23 | Zoom | ZOOM |
| 24 | Focus | FOCUS |
| 25 | Frame Rotation (±55°) | EFFECTS |
| 26–33 | Blades 1A/1B/2A/2B/3A/3B/4A/4B | DUMMY |
| 34 | Shutter/Strobe | SHUTTER |
| 35 | Dimmer | DIM |

### Особенности

- **RGBAL** (добавлен Amber + Light Green) — 5-цветный модуль обеспечивает CRI≥95
- Virtual CMY: прибор программно переводит CMY → RGBAL через iCC
- В 64CH режиме можно управлять каждым цветом RGBAL раздельно (16-bit)
- 165 электронных цветовых фильтров в Virtual Color Wheel (эмуляция плёночных гелей LEE/Rosco)
- Шумовой уровень: 27–28 dB (ultra-silent режим)

---

## 4. Super Scope II

**Тип**: 4-in-1 LED Moving Head Profile Spot  
**Производитель**: Light Sky  
**Источник света**: 520W White LED  
**Световой поток**: 20000 Lm | **Освещённость**: 24500 lux @ 10m  
**Зум**: 3.8°–50° | **Линза**: 140mm  
**Pan/Tilt**: 540° / 270°  
**Мощность**: 960W | **IP**: IP20  
**Цветовая система**: CMY ∞ + CTO 3000–7000K + Color Wheel (6 цветов+CRI+blank)  
**CRI**: ≥72 (≥88 с High CRI фильтром)

### DMX режимы

| Режим | Каналы | Назначение |
|-------|--------|-----------|
| Standard | 42CH | Основной: CMY 8-bit, Zoom/Focus/Dim 16-bit |
| Extended | 54CH | CMY 16-bit, Blade fine каналы |

### Ключевые DMX каналы (42CH)

| Ch | Функция |
|----|---------|
| 1+2 | PAN 16-bit |
| 3+4 | TILT 16-bit |
| 5 | Speed |
| 6 | Functions |
| 7 | Cyan |
| 8 | Magenta |
| 9 | Yellow |
| 10 | CTO |
| 11 | Colour Wheel |
| 12 | Gobo Wheel 1 |
| 13 | Gobo 1 Rotation |
| 14 | Gobo Wheel 2 |
| 15 | Gobo 2 Rotation |
| 16–23 | Blades 1A/1B/2A/2B/3A/3B/4A/4B |
| 24 | Frame Rotation |
| 25 | Frame Macro (preset shapes) |
| 26 | Frame Macro Zoom |
| 27 | Prism (4-facet + 4-linear) |
| 28 | Prism Rotation |
| 29 | Effect/Animation Wheel |
| 30 | Effect Rotation |
| 31 | Frost (light + heavy) |
| 32 | Iris |
| 33+34 | Zoom 16-bit |
| 35+36 | Focus 16-bit + Autofocus |
| 37 | Autofocus Distance |
| 38 | Autofocus Adjustment |
| 39 | Strobe |
| 40+41 | Dimmer 16-bit |
| 42 | Gobo Macro |

### Framing Macro (ch25) — preset shapes

0: none | 11–20: Square | 21–30: Rectangle | 31–40: Isosceles Tri | 41–50: Trapezoid  
51–60: Fan Up | 61–70: Parallelogram | 71–80: Right Angle Trap | 81–90: Fan Down  
91–100: Triangle | 101–110: Prism | 111–120: Stripes | 121–130: Bar  
131–140: ↖ quadrant | 141–150: Top semi | 151–160: ↗ quadrant | ...

---

## 5. Super Scope Pro

**Тип**: 4-in-1 LED Moving Head Profile Spot  
**Производитель**: Light Sky  
**Источник света**: 450W White LED  
**Световой поток**: 20000 Lm | **Освещённость**: 24000 lux @ 10m  
**Зум**: 4°–53° | **Линза**: 133mm  
**Pan/Tilt**: 540° / 270°  
**Мощность**: 620W | **IP**: IP20  
**Цветовая система**: CMY ∞ + CTO 3000–6500K + Color Wheel (5 цветов+CRI+white)  
**CRI**: ≥70 (≥90 с CRI фильтром)

### DMX режимы

| Режим | Каналы | Назначение |
|-------|--------|-----------|
| Standard | 33CH | Основной: CMY 8-bit, Zoom/Focus 8-bit |
| Extended | 36CH | + Speed ch, Zoom/Focus 16-bit |

### Ключевые DMX каналы (33CH vs 36CH)

| 33CH | 36CH | Функция |
|------|------|---------|
| 1+2 | 1+2 | PAN 16-bit |
| 3+4 | 3+4 | TILT 16-bit |
| — | 5 | Speed (только в 36CH) |
| 5 | 6 | DeviceSet/Functions |
| 6 | 7 | Cyan |
| 7 | 8 | Magenta |
| 8 | 9 | Yellow |
| 9 | 10 | Virtual Color Wheel |
| 10 | 11 | Gobo Wheel (7 гобо) |
| 11 | 12 | Gobo Rotation |
| 12 | 13 | CTO |
| 13 | 14 | Animation Wheel |
| 14–21 | 15–22 | Blades A1/A2/B1/B2/C1/C2/D1/D2 |
| 22 | 23 | Frame Rotation |
| 23 | 24 | Iris |
| 24 | 25 | Prism (position + rotation в 1 канале!) |
| 25 | 26 | Frost |
| 26 | 27 | Effect Macro |
| 27 | 28 | Focus 8-bit |
| — | 29 | Focus Fine (16-bit в 36CH) |
| 28 | 30 | Zoom 8-bit |
| — | 31 | Zoom Fine (16-bit в 36CH) |
| 29 | 32 | Strobe |
| 30+31 | 33+34 | Dimmer 16-bit |
| 32 | 35 | AutoFocus Distance |
| 33 | 36 | AutoFocus Fine |

### Особенности Pro

- **Prism канал (ch24/25)**: один канал совмещает позицию И вращение призмы (0–63: индексация, 64–127: CW вращение, 128–191: CCW вращение, 192+: swing эффекты)
- 1 гобо колесо vs 2 у Plus/II
- Только **1 frost** (light) vs 2 у Plus

---

## 6. Super Scope Plus

**Тип**: 4-in-1 LED Moving Head Profile Spot  
**Производитель**: Light Sky  
**Источник света**: 880W White LED  
**Световой поток**: 41000 Lm | **Освещённость**: 28300 lux @ 10m  
**Зум**: 5.5°–52° | **Линза**: 180mm  
**Pan/Tilt**: 540° / 270°  
**Мощность**: 1400W | **IP**: IP20  
**Цветовая система**: CMY ∞ + CTO 2800–6800K + Color Wheel (5 цветов+CRI+blank)  
**CRI**: ≥71 (≥90 с CRI фильтром)

### DMX режимы

| Режим | Каналы | Назначение |
|-------|--------|-----------|
| Standard | 43CH | Основной: CMY 8-bit, Zoom/Focus/Dim 16-bit |
| Extended | 55CH | CMY 16-bit, Blade fine каналы |

### Ключевые DMX каналы (43CH)

| Ch | Функция |
|----|---------|
| 1–5 | PAN/TILT 16-bit + Speed |
| 6 | Functions |
| 7 | Cyan |
| 8 | Magenta |
| 9 | Yellow |
| 10 | CTO |
| 11 | Colour Wheel |
| 12+13 | Gobo Wheel 1 + Rotation |
| 14+15 | Gobo Wheel 2 + Rotation |
| 16–23 | Blades 1A/1B/2A/2B/3A/3B/4A/4B |
| 24 | Frame Rotation |
| 25 | Frame Macro |
| 26 | Frame Macro Zoom |
| 27+28 | Prism + Prism Rotation |
| 29+30 | Effect + Effect Rotation |
| 31 | **Frost 1** |
| 32 | **Frost 2** (только у Plus!) |
| 33 | Iris |
| 34+35 | Zoom 16-bit |
| 36+37 | Focus 16-bit |
| 38+39 | Autofocus |
| 40 | Strobe |
| 41+42 | Dimmer 16-bit |
| 43 | Gobo Macro |

### Отличия Plus от II

| Параметр | Super Scope II | Super Scope Plus |
|----------|---------------|-----------------|
| Мощность | 520W | 880W |
| Световой поток | 20000 Lm | 41000 Lm |
| Линза | 140mm | 180mm |
| Prism | 4-facet + 4-linear | 4-facet + 4-linear |
| Frost | 2 (light/heavy) | **2 независимых канала** (ch31+32) |
| Weight | 28.3 kg | 37.5 kg |
| Размеры | 442×267×656mm | 442×282×788mm |

---

## Сравнительная таблица всех приборов

| Параметр | IL-ENERGY 19 HC | Aquapearl-Pro II | SSColor | SS II | SS Pro | SS Plus |
|----------|----------------|-----------------|---------|-------|--------|---------|
| Тип | Wash | Wash | Profile | Profile | Profile | Profile |
| Источник | 19×40W RGBWW | 19×40W RGBW | 600W RGBAL | 520W White | 450W White | 880W White |
| Lm | н/д | н/д | 17600 | 20000 | 20000 | 41000 |
| Зум | 5–45° | 5–45° | 5.9–52° | 3.8–50° | 4–53° | 5.5–52° |
| Линза | — | — | 180mm | 140mm | 133mm | 180mm |
| Pan/Tilt | 540/218° | 540/218° | 540/270° | 540/270° | 540/270° | 540/270° |
| CMY | нет | нет | Virtual | ✓ | ✓ | ✓ |
| CTO | ✓ | ✓ | 2700–8000K | 3000–7000K | 3000–6500K | 2800–6800K |
| Gobos | нет | нет | 2×7 | 2×7 | 1×7 | 2×7 |
| Prism | нет | нет | 8-facet | 4-facet+4L | 4-facet | 4-facet+4L |
| Framing | нет | нет | 4 blades | 4 blades | 4 blades | 4 blades |
| Frost | нет | нет | 3 modes | 2 modes | 1 mode | 2 channels |
| Iris | нет | нет | ✓ | ✓ | ✓ | ✓ |
| Pixel | 76CH | 98CH | нет | нет | нет | нет |
| IP | IP66 | IP66 | IP20 | IP20 | IP20 | IP20 |
| Вт | 730W | 730W | 1050W | 960W | 620W | 1400W |
| MA2 режимы | 4 файла | 3 файла | 35+60CH | 42+54CH | 33+36CH | 43+55CH |
| Источник MA2 | Сгенерирован | Сгенерирован | Сгенерирован | Сгенерирован | Сгенерирован | Сгенерирован |

---

## Важные DMX особенности

### Framing Macro (SS II и SS Plus, ch25/37)
Предустановленные формы кадрирования командой (hold 0.5s на значении):
- Square, Rectangle, Triangle, Trapezoid, Fan, Parallelogram, Semi-circle, Bar и т.д.
- **Framing Macro Zoom** (ch26/38): масштабирование выбранной формы 0–255

### Autofocus (SS II / SS Pro / SS Plus)
- **Autofocus Distance** (ch37/32/38): 7M/10M/15M/20M/25M/30M/40M/50M
- **Autofocus Adjustment** (ch38/33/39): тонкая подстройка
- В MA2 профиле оба mapped на DUMMY — управлять через channel faders

### Super Scope Pro: комбинированный канал Prism (33CH, ch24)
Один канал совмещает:
- 0–9: Prism out
- 10–63: Prism In + indexing (0–360°)
- 64–127: CW вращение fast→slow
- 128–191: CCW вращение slow→fast
- 192–255: swing эффекты (90°/180°/270°/360°)

### Super Scope Color: Virtual Colour Wheel (ch8)
165 предустановленных цветовых фильтров (0–231 DMX):
- Эмуляция плёночных гелей LEE и Rosco
- Значения 133–231: мультиколор эффекты (только с prism/gobo/effect wheel)
- 236–255: Rainbow эффекты

### IL-ENERGY / Aquapearl: Pixel Crossfade (Extended режим)
- Crossfade DMX→pixel engine (0=full DMX, 255=full pixel)
- Позволяет смешивать внешнее управление с pixel pattern эффектами
