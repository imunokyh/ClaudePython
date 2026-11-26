# Door Lock Control ECU — Software Requirements Specification v1.2

## 1. Interfaces

| Signal | Dir | Range | Resolution | Cycle | Note |
|---|---|---|---|---|---|
| VehSpd | In (CAN) | 0–250 km/h | 1 km/h | 20 ms | Invalid value 0xFF = signal invalid |
| IgnState | In | OFF / ACC / ON | - | 20 ms | |
| GearPos | In | P / R / N / D | - | 20 ms | |
| CrashDetected | In (Airbag ECU) | 0 / 1 | - | 10 ms | E2E protected (CRC, Alive counter) |
| LockSwitch | In | NONE / LOCK / UNLOCK | - | event | driver door switch |
| DoorOpen_FL/FR/RL/RR | In | CLOSED / OPEN | - | 20 ms | |
| DoorLockCmd | Out | NONE / LOCK / UNLOCK | - | event | |

## 2. Functional requirements

- **SWR-DL-001** (QM): When IgnState = ON and VehSpd rises to 15 km/h or more, the SW shall send DoorLockCmd = LOCK within 500 ms, provided all doors are CLOSED.
- **SWR-DL-002** (QM): The auto-lock of SWR-DL-001 shall be sent only once per drive cycle (IgnState OFF→ON).
- **SWR-DL-003** (QM): When GearPos changes to P and IgnState = ON, the SW shall send DoorLockCmd = UNLOCK within 300 ms.
- **SWR-DL-004** (QM): When LockSwitch = LOCK is received, the SW shall send DoorLockCmd = LOCK within 200 ms. When LockSwitch = UNLOCK is received and VehSpd < 5 km/h, the SW shall send DoorLockCmd = UNLOCK within 200 ms.
- **SWR-DL-005** (ASIL B): When CrashDetected = 1 is received, the SW shall send DoorLockCmd = UNLOCK within 100 ms, regardless of any other input.
- **SWR-DL-006** (QM): If any door is OPEN, the auto-lock of SWR-DL-001 shall not be executed.

## 3. Non-functional requirements

- **SWR-DL-101** (ASIL B): If the CrashDetected message fails the E2E check (CRC error or Alive counter not incremented) for 3 consecutive cycles, the SW shall treat the signal as faulty, keep the last valid lock state and set DTC 0xB1234.
- **SWR-DL-102** (QM): The SW shall complete initialization within 150 ms after power-up and be ready to process inputs.
- **SWR-DL-103** (QM): The door lock function shall respond fast enough under all bus load conditions.
