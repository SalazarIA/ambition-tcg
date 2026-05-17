# Ascension Duel Rulebook

## Goal

Break the rival by reducing their HP to 0. The duel can also be decided by a successful Domination strike when the Ambition Core is high enough.

## Core Loop

1. Start a Round.
2. Draw.
3. Choose one Intent: Strike, Guard, Focus or Scheme.
4. Play cards by legal purpose.
5. Commit.
6. Resolve the Mind Clash.
7. Write the Chronicle.
8. Continue until a winner is set.

## Champion Rule

Each side has exactly one active Champion slot. Summoning a new Champion moves the previous active Champion to Echo. If a side has no active Champion, incoming pressure is more dangerous.

## Bound Souls

Champions in hand may be Bound as Souls to the active Champion. A Champion can hold up to three Bound Souls. Bound Souls modify clash scoring through pressure, guard, Ambition, draw or recovery bonuses.

## Card Purposes

- **Summon:** make a Champion active.
- **Bind:** attach a Champion as a Bound Soul.
- **Burn:** move a card to Echo and gain Ambition.
- **Cast:** resolve a Technique immediately.
- **Equip:** make a Relic the persistent modifier. Replaced Relics move to Echo.
- **Set:** prepare a Scheme.
- **Ascend:** spend Ambition to evolve the active Champion.

## Intent Matrix

- Strike pressures Focus.
- Guard contains Strike.
- Focus outscales Guard.
- Scheme punishes repeated or predictable Intent.
- Mirror Intents produce controlled neutral effects instead of runaway damage.

## Schemes

Schemes are prepared effects. They may trigger on repeated Intent, Strike into Guard, opponent Focus or mirrored psychology. Hidden enemy Schemes are not exposed in public payloads.

## Domination

Domination is a risky finisher. It requires a high Ambition Core and an active Champion. If successful, it deals massive pressure. If it fails, the Ambition is lost and the acting side becomes vulnerable.

## Deadlock Prevention

If a side reaches clash resolution without an Intent, the engine defaults that side to Focus. The bot always attempts to summon, choose Intent, play or burn and proceed.
