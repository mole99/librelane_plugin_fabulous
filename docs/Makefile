FILES_ODG := $(wildcard odg/*.odg)

FILES_SVG = $(patsubst odg/%.odg,svg/%.svg,$(FILES_ODG))
FILES_PNG = $(patsubst odg/%.odg,png/%.png,$(FILES_ODG))
FILES_PDF = $(patsubst odg/%.odg,pdf/%.pdf,$(FILES_ODG))

all: $(FILES_SVG) $(FILES_PNG) $(FILES_PDF)

svg/%.svg: odg/%.odg
	soffice --convert-to svg --outdir svg/ $<

png/%.png: odg/%.odg
	soffice --convert-to png --outdir png/ $<

pdf/%.pdf: odg/%.odg
	soffice --convert-to pdf --outdir pdf/ $<

clean:
	rm png/*
	rm svg/*
	rm pdf/*
