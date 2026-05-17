# Ascension Taxonomy Migration

The public Ascension flow uses five canonical card purposes:

- Champion
- Technique
- Relic
- Scheme
- Ascension

Legacy taxonomy remains internal compatibility only. Old creature-like cards map to Champion, direct action cards map to Technique, persistent objects map to Relic, prepared effects map to Scheme and finisher cards map to Ascension.

New public routes must not use legacy type labels as primary product language. Existing legacy routes may still expose old labels because they preserve the retired Arena contract.

Canonical helper: `services/ascension_taxonomy.py`.
