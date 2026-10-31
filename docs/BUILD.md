# 재빌드

## 준비물

- 원본 ISO `Inuyasha - Feudal Combat (USA).iso` (README의 해시와 일치해야 함)를 저장소 루트에 둡니다.
- Python 3.13, `numpy`, `Pillow`, `opencv-python`, `pycdlib`
- 글꼴(`docs/FONT_CREDITS.md`):
  - 저장소 루트: `NanumSquareNeo-dEb.ttf`, `NanumSquareNeo-eHv.ttf`, `SeoulHangangEB.ttf`
  - `work/fonts/Galmuri11-Bold.ttf`
- xdelta3 (배포 파일을 만들 때만)

## 빌드

```powershell
python -I tools/unpack_iso.py      # 원본 ISO 의 FPACK/·실행파일 → work/ext
python -I tools/build.py           # → Inuyasha - Feudal Combat (USA) (Korean).iso
```

결과 ISO의 SHA-256이 `release_manifest.json`의 `output_iso_sha256`과 같아야 합니다.

## 배포 파일

```powershell
xdelta3 -e -0 -S none -A -s "Inuyasha - Feudal Combat (USA).iso" "Inuyasha - Feudal Combat (USA) (Korean).iso" Inuyasha_Feudal_Combat_PS2_KO_v1.0.xdelta
```

실행파일이 바뀌면 게임 CRC(실행파일을 4바이트 단위로 XOR한 값, `tools/emu.py`의 `elf_crc`)를 다시 계산해 `patches/SLUS-21193_<CRC>.pnach`의 이름과 `gametitle`을 맞추고, 와이드 패치 주소의 원래 명령이 그대로인지 확인합니다.

## 번역 추가

`translation/src.tsv`는 원문 대조표(`id, 출현수, 최소 슬롯, 첫 파일, 원문`)입니다. 번역은 같은 id로 `ko_ui.tsv`, `ko_story.tsv`, `ko_mission.tsv`에 씁니다(`\n` = 줄바꿈).
