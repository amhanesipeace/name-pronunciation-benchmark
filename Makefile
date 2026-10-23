# Reproducible benchmark pipeline.
#
#   make setup            install Python dependencies
#   make gtts             gTTS: synthesize -> score -> analyze (isolated names)
#   make gtts-carrier     gTTS with carrier sentences
#   make espeak           espeak-ng (needs the espeak-ng binary)
#   make mms              Meta MMS neural (needs torch/transformers)
#   make mms-carrier      MMS with carrier sentences
#   make forest           forest plot of the gap (all runs, 95% CIs)
#   make per-language-forest   per-language gap vs English for the gTTS run
#   make cross-engine     per-name CER agreement between two engines (carrier)
#   make length-check     robustness: is the gap just a name-length effect?
#   make errors           qualitative error tables from the gTTS run
#   make test             run the unit tests
#   make all              gtts + gtts-carrier + mms-carrier + errors
#   make clean            remove all generated outputs
#
# PYTHON lets you point at a venv, e.g.  make gtts PYTHON=.venv/bin/python
PYTHON ?= python
NAMES  ?= data/names.csv
MODEL  ?= base

# $(call pipeline,<engine>,<outdir>,<extra run.py args>)
define pipeline
	$(PYTHON) run.py --engine $(1) --names $(NAMES) --out $(2) $(3)
	$(PYTHON) score.py --run $(2) --model $(MODEL)
	$(PYTHON) analyze.py --scores $(2)/scores.csv --out $(2)/analysis --title "$(1) $(3)"
endef

.PHONY: setup gtts gtts-carrier espeak mms mms-carrier errors test all clean \
        sensitivity forest per-language-forest cross-engine length-check

setup:
	$(PYTHON) -m pip install -r requirements.txt

gtts:
	$(call pipeline,gtts,outputs,)

gtts-carrier:
	$(call pipeline,gtts,outputs_gtts_carrier,--carrier)

espeak:
	$(call pipeline,espeak,outputs_espeak,)

mms:
	$(call pipeline,mms,outputs_mms,)

mms-carrier:
	$(call pipeline,mms,outputs_mms_carrier,--carrier)

errors:
	$(PYTHON) error_analysis.py --scores outputs/scores.csv --top 5 \
		--out docs/error_analysis_gtts.md

sensitivity:
	$(PYTHON) sensitivity.py --run outputs --models tiny base small

forest:
	$(PYTHON) forest_plot.py

per-language-forest:
	$(PYTHON) per_language_forest.py --run outputs

cross-engine:
	$(PYTHON) cross_engine.py --run-a outputs_gtts_carrier --run-b outputs_mms_carrier

length-check:
	$(PYTHON) length_confound.py --run outputs

test:
	$(PYTHON) -m pytest

all: gtts gtts-carrier mms-carrier errors
	@echo "Done. See outputs*/analysis/ for charts + stats, docs/ for tables."

clean:
	rm -rf outputs outputs_*/
