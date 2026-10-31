# 권리 및 외부 자료

이 저장소는 비공식 한국어 패치의 제작 소스·번역·검증 자료를 공개하기 위한 것입니다. 「Inuyasha: Feudal Combat」과 그 텍스트·이미지·음성·실행 코드의 권리는 원 권리자(BANDAI NAMCO, 제작 EIGHTING)에게 있습니다. 「이누야샤」 원작의 권리는 다카하시 루미코·쇼가쿠칸·요미우리TV·선라이즈에 있습니다.

배포하지 않는 것은 원본 게임, 패치를 적용한 게임, 게임에서 추출한 실행파일·텍스처·음성·글꼴입니다. 릴리즈에는 원본 디스크 이미지가 있어야만 쓸 수 있는 차분 파일(xdelta)과, 실행파일 명령 6개를 바꾸는 PCSX2 패치 파일(pnach)만 첨부합니다.

와이드 패치(`patches/SLUS-21193_64836393.pnach`)는 PCSX2 패치 데이터베이스의 `SLUS-21193_E246AA30.pnach`(제작 Little Giant)를 한글판 CRC로 옮긴 것이며, 패치 내용은 바꾸지 않았습니다. 원 패치의 권리와 라이선스는 [PCSX2 patches](https://github.com/PCSX2/pcsx2_patches) 프로젝트를 따릅니다.

저장소를 공개했다고 해서 모든 파일에 같은 오픈소스 라이선스를 부여한다는 뜻은 아닙니다. 자체 제작 코드와 번역 전체에 대한 포괄 라이선스는 따로 지정하지 않았습니다.

`translation/src.tsv`에는 번역 대조를 위해 게임의 영어 원문이 들어 있습니다. 원문의 권리 역시 원 권리자에게 있습니다.

게임 안 한글은 다음 글꼴로 그렸습니다. 글꼴 파일 자체는 저장소에 넣지 않았습니다(`docs/FONT_CREDITS.md` 참고).

- 나눔스퀘어 네오(NAVER), SIL Open Font License 1.1 — `LICENSES/`에 전문 보존
- 갈무리11(Minseo Lee), SIL Open Font License 1.1 — `LICENSES/`에 전문 보존
- 서울한강체(서울특별시), 서울서체 이용 약관

xdelta, PCSX2, Python 라이브러리(numpy, Pillow, scipy, pycdlib) 등 외부 도구는 각 프로젝트의 라이선스를 따르며, 바이너리는 재배포하지 않습니다. 게임 코드를 디스어셈블한 결과물은 넣지 않았고, 해석한 내용만 `docs/TECHNICAL.md`에 정리했습니다. 단, 실행파일에 넣은 짧은 MIPS 코드는 `tools/build.py`에 들어 있습니다.
