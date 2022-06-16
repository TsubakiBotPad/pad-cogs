HELP_TEXT = """PADle is a Wordle-inspired guessing game, but with some differences!
{db} You are not guessing words! Instead, you are guessing monsters.
{db} The difference is based on awakenings, rarity, monster points, and a few other attributes. \
Your current score screen will tell you if your guesses are correct, wrong, or misplaced (for awakenings).
{db} Because this can be much harder than guessing words, you have infinite guesses!
{db} Like Wordle, you can guess any monster, but only certain monsters can be the final PADle. \
See `{p}padle validrules` to see what monsters count as "valid" final PADles.
{db} Share your number of guesses with `{p}padle score`!

To see the main menu at any time, type `{p}padle`. To see this specific greeting again, type `{p}padle help`.

Happy puzzling! {tsubaki}"""

RULES_TEXT = """Valid monsters include the following:
{db} Super Reincarnated evolutions of pantheons
{db} 50k+ MP AND [have a Super Awakening OR are max transformed]
{db} 15k MP AND are non-event AND [have a Super Awakening OR are max transformed]
        
The following monsters are exceptions to the above and will NOT be included:
{rd} Collab monsters (note this does not exclude Event monsters such as from Heroine or Relic Saga)
{rd} An equip evolution
{rd} Monsters not on the NA server
{rd} Monsters that are not max-transformed

*NOTE: The Super Awakening check ensures monsters chosen are max-evo, for the most part.*
"""