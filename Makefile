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
#   make taxonomy         how names fail: recovered / English-sub / garbled
#   make errors           qualitative error tables from the gTTS run
#   make figures          regenerate EVERY committed figure/report from the
#                         committed scores (no TTS/ASR stack; skips sensitivity)
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
        sensitivity forest per-language-forest cross-engine length-check taxonomy \
        figures

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

taxonomy:
	$(PYTHON) error_taxonomy.py --run outputs

# Regenerate every committed figure/report straight from the committed score
# tables (no TTS/ASR stack). analyze.py also writes summary.csv/stats.txt, so its
# charts go through a tmp dir and only the PNG is kept, leaving docs/ clean.
figures:
	$(PYTHON) comparison_charts.py all
	$(PYTHON) forest_plot.py
	$(PYTHON) per_language_forest.py --run outputs
	$(PYTHON) cross_engine.py --run-a outputs_gtts_carrier --run-b outputs_mms_carrier
	$(PYTHON) error_taxonomy.py --run outputs
	$(PYTHON) length_confound.py --run outputs
	$(PYTHON) error_analysis.py --scores outputs/scores.csv --top 5 --out docs/error_analysis_gtts.md
	$(PYTHON) aggregate_results.py
	$(PYTHON) analyze.py --scores outputs/scores.csv --out docs/_tmp --title "gtts n=80" && mv docs/_tmp/cer_by_language.png docs/cer_by_language.png
	$(PYTHON) analyze.py --scores outputs_ext_gtts/scores.csv --out docs/_tmp --title "gtts n=120" && mv docs/_tmp/cer_by_language.png docs/cer_by_language_ext120.png
	$(PYTHON) analyze.py --scores outputs_ext_gtts_carrier/scores.csv --out docs/_tmp --title "gtts carrier n=120" && mv docs/_tmp/cer_by_language.png docs/cer_gtts_carrier_ext120.png
	$(PYTHON) analyze.py --scores outputs_ext_mms_carrier/scores.csv --out docs/_tmp --title "mms carrier n=120" && mv docs/_tmp/cer_by_language.png docs/cer_mms_carrier_ext120.png
	@rm -rf docs/_tmp
	@echo "All figures regenerated from committed scores (sensitivity needs audio)."

test:
	$(PYTHON) -m pytest

all: gtts gtts-carrier mms-carrier errors
	@echo "Done. See outputs*/analysis/ for charts + stats, docs/ for tables."

clean:
	rm -rf outputs outputs_*/
