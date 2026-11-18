"""Prompts used only by scenario creation."""

from __future__ import annotations




TASK_REASONABLENESS_SYSTEM_PROMPT = """Review one generated DCB task as a user-intent quality agent. Decide whether the rule-built request is coherent, meaningful, and plausible for the supplied world and task category.

An intentional nonexistent-target or unsupported-property request marked as infeasible in the private semantic summary is valid. Its public instruction should state only the requested task, without failure-handling guidance. Reject only nonsensical, self-contradictory, meaningless, or clearly implausible user intent.

Respond with reasoning in <think> and exactly one JSON object in <answer> following the structure below:
```json
{
    "judge": <true or false>,
    "explanation": <a short explanation if this task failed its judgment>
}
```
"""

TASK_REASONABLENESS_USER_PROMPT = """Judge intent quality only, using the public world, template candidates, and private semantic summary below.

Task id: {task_id}
Task family: {task_family}
Task subtype: {task_subtype}

Resolved public world summary:
```json
{world_summary}
```

Template instruction candidate(s):
{instruction_template}

Private semantic summary:
{seed_summary}
"""

TASK_REWRITE_SYSTEM_PROMPT = """Rewrite one template-created DCB instruction into the requested language style.

All supplied template instructions express the same task. Device references may differ because multiple names uniquely identify the same device in this world. In every style, you may choose any of these supplied references; preserve the chosen template's task information and identifying qualifiers. Do not combine the equivalent templates into additional requests.

Write device and space references as natural lowercase prose without quotation marks. In direct, preserve object-model property names, operation names, class/type identifiers, and literal values verbatim, including their spelling and underscores. In concise and polite, minor terminology changes are allowed, but keep all target qualifiers and task information explicit. Conversational, distracting, and folk may translate technical wording into everyday expressions with limited meaning shifts, but must retain all concrete numeric values, amounts, ranges, top-k counts, and requested activities. They may shorten target references using the layout when the target remains clear. Only implicit may omit numbers, ranges, technical distinctions, and target qualifiers, expressing the broad intent through approximate or ambiguous requests. Use the supplied layout to ground these requests in the actual environment. Broader device names and contextual references are allowed. Do not invent a user location or unrelated objectives.

For distracting, use conversational wording and add user chatter that does not change the requested task: things the user did today, their mood, plans for tomorrow, opinions or evaluations, or meaningless expressions. The chatter may concern the current environment, other environments, the task's devices, or other devices; it does not have to be about a different topic from the task. You may invent these asides, including environmental observations and device anecdotes, placing them before, between, or after task clauses. They must not introduce additional requests, change task targets, conditions, or timing, invent the user's current location, or supply query answers or private memory values. Ground task targets in the supplied layout; mentioning another environment or device in an aside does not make it a task target. Removing the chatter must leave the same conversational task. Other styles do not add this distracting content.

An intentionally missing device/space, unsupported property/capability, or invalid literal is fixed by the template. Preserve the exact identity and offending property/value in every style, including implicit. Never invent a different missing attribute during rewriting, repair the request into a feasible one, or replace an actual literal such as 12 degrees with the label "invalid value". State the request without revealing its feasibility or expected report.

Preserve data dependencies in every style: if a Query supplies a later request's target or value, that request must still use the Query result. Keep independent requests independent. Never replace a failed Query with a guessed target/value, drop an independent executable request, or reveal internal atom IDs, failure statuses, or reason codes in the instruction.

Device Control instructions refer to the named device setting; environmental Goal instructions refer to the actual space property. For a terminal Goal, use bring, reach, or match, not keep or maintain. Preserve this distinction outside the implicit style.

Query answer formatting is defined by the benchmark prompt. Omit answer-format directives, including JSON serialization, answer wrapping, and sorting by names or IDs. Ranking tie handling is also defined by the benchmark prompt; omit phrases such as "including boundary ties" from the rewritten task. In every style except implicit, retain the candidate scope, ranking intent, exact top-k count, and action order. Only implicit may express these more loosely while keeping the overall query or action intent recognizable.

When a target value comes from memory, do not state or infer its private literal value. Direct, concise, and polite must retain the saved-preference cue. Conversational, distracting, and folk may phrase it naturally, such as "Kate's usual setting", while preserving the preference source. Implicit may leave the memory cue unstated. For a saved-preference Goal, ask to match that preference without spelling out evaluator tolerance amounts, tolerance ranges, or endpoint-inclusion rules. Every style except implicit must retain explicit goal values and ranges. Only implicit may replace them with qualitative goals such as brighter, a little quieter, or comfortable. Preserve any request to create or update memory from a Query result, without supplying that result in advance. Never expose internal device or space IDs.

Within the instruction field, express requests in natural language, never as tool calls or API syntax. Do not encode actions using function-call notation, empty parentheses, parameter assignments, or JSON objects. Follow the requested style's terminology and value-preservation rules while expressing arguments in prose: for example, "set power (value=true)" becomes "set power to true", "delete clip (clip_id="clip_1")" becomes "delete clip with clip_id clip_1", and "resume guidance ()" becomes "resume guidance". Use natural singular and plural forms such as "1 minute" and "2 minutes", never the optional suffix in "minute(s)". Parentheses may clarify ordinary prose. Preserve parentheses, equals signs, or other punctuation when they belong to a required literal name or text value; do not treat them as API formatting. These wording rules apply to the instruction text, not the required JSON response wrapper.

Target instruction style: {instruction_style}

Description:
{instruction_style_description}

Examples:
{instruction_style_examples}


Examples illustrate wording only; never copy their entities, values, or objectives into this task. An example's layout applies only to that example. Use the actual task layout when shortening references. Direct, concise, and polite retain complete task information. Conversational, distracting, and folk retain concrete values while changing expression, allowing limited everyday reinterpretation. Exact number words such as "two" for 2 are allowed outside direct; "a bit" is not a substitute for a concrete amount. Only implicit may transform precise instructions into vague intent-based requests without restating numbers or technical details. Keep the overall requested activities recognizable and never supply a query answer in advance.

Respond with reasoning in <think> and exactly one JSON object in <answer> following the structure below:
```json
{{
    "instruction": <the rewritten instruction>
}}
```
"""

TASK_REWRITE_USER_PROMPT = """The complete set of equivalent template instructions is provided below, including available device-name variants. Refer to all candidates and produce one rewrite in the requested style. Choose a supplied device reference that uniquely identifies the intended target.

Task id: {task_id}
Task family: {task_family}
Task subtype: {task_subtype}

Public space and device layout (IDs identify layout entries; do not copy internal IDs into the instruction):
```json
{world_layout}
```

Template instruction candidate(s):
{instruction_template}
"""

INSTRUCTION_STYLE_EXAMPLES = {'direct': {'description': '\n'
                           'Tone: Neutral, explicit commands without conversational framing.\n'
                           'Information: Keep every action, target qualifier, value, unit, '
                           'condition, selection rule, and execution order explicit.\n'
                           'Terminology: Preserve object-model property names, operation names, '
                           'class/type identifiers, and literal values verbatim; change only the '
                           'surrounding prose.\n'
                           'References: Retain all supplied space, device, and person qualifiers '
                           'even when the layout would allow a shorter reference.\n'
                           'Structure: State the requested actions directly in clear, complete '
                           'clauses.\n'
                           'Avoid: Greetings, courtesy phrases, informal substitutes for model '
                           'terms, omitted information, and invented context.\n'
                           '            ',
            'examples': [{'input': 'Tell me the current temperature of the space named Kitchen.',
                          'rewrite': 'Report the current temperature of the kitchen.'},
                         {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and increase '
                                   'color_temperature by 300.',
                          'rewrite': 'Decrease brightness by 10 and increase color_temperature by '
                                     '300 on dining room lamp 8.'},
                         {'input': "Bring the illuminance in Stairs into line with Kate's saved "
                                   'preference.',
                          'rewrite': "Bring the stairs' illuminance into line with Kate's saved "
                                     'preference.'},
                         {'input': 'Compare current noise among Entryway, Laundry Room, Living '
                                   'Room; list every target in the top 2 positions for highest '
                                   'noise.',
                          'rewrite': 'Compare the current noise in the entryway, laundry room, and '
                                     'living room. List every space in the top 2 positions for '
                                     'highest noise.'},
                         {'input': 'Please change all bluetooth speaker devices as follows: adjust '
                                   'playback_content upward by 2 and adjust volume downward by 10. '
                                   'Then tell me the current temperature in Kitchen. Then, for all '
                                   'living_room spaces, work toward this outcome: increase their '
                                   'illuminance by about 100, ending between 780 and 820.',
                          'rewrite': 'Increase playback_content by 2 and decrease volume by 10 on '
                                     'all bluetooth speaker devices. Then report the current '
                                     'temperature of the kitchen. Then, for all living_room '
                                     'spaces, increase their illuminance by about 100, ending '
                                     'between 780 and 820.'}]},
 'concise': {'description': '\n'
                            'Tone: Brief, neutral instructions with minimal wording.\n'
                            'Information: Keep every action, target qualifier, value, unit, '
                            'condition, selection rule, and execution order explicit.\n'
                            'Terminology: Allow minor, meaning-preserving wording changes, such as '
                            'color_temperature to color temperature; retain the exact operation '
                            'and values.\n'
                            'References: Retain all supplied space, device, and person qualifiers; '
                            'shorten wording without omitting task information.\n'
                            'Structure: Use compact clauses, fragments, or semicolons while '
                            'keeping all steps understandable.\n'
                            'Avoid: Courtesy phrases, filler, ambiguous abbreviations, omitted '
                            'qualifiers, and invented context.\n'
                            '            ',
             'examples': [{'input': 'Tell me the current temperature of the space named Kitchen.',
                           'rewrite': 'Current temperature in the kitchen?'},
                          {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and '
                                    'increase color_temperature by 300.',
                           'rewrite': 'Lamp 8 in the dining room: decrease brightness by 10; '
                                      'increase color temperature by 300.'},
                          {'input': "Bring the illuminance in Stairs into line with Kate's saved "
                                    'preference.',
                           'rewrite': "Bring the stairs' illuminance into line with Kate's "
                                      'preference.'},
                          {'input': 'Compare current noise among Entryway, Laundry Room, Living '
                                    'Room; list every target in the top 2 positions for highest '
                                    'noise.',
                           'rewrite': 'Among the entryway, laundry room, and living room, list the '
                                      'top 2 noisiest rooms.'},
                          {'input': 'Please change all bluetooth speaker devices as follows: '
                                    'adjust playback_content upward by 2 and adjust volume '
                                    'downward by 10. Then tell me the current temperature in '
                                    'Kitchen. Then, for all living_room spaces, work toward this '
                                    'outcome: increase their illuminance by about 100, ending '
                                    'between 780 and 820.',
                           'rewrite': 'All bluetooth speakers: increase playback content by 2; '
                                      'decrease volume by 10. Then report current kitchen '
                                      'temperature. Then, for all living rooms, increase '
                                      'illuminance by about 100, ending between 780 and 820.'}]},
 'polite': {'description': '\n'
                           'Tone: Courteous, natural dialogue, more formal than conversational or '
                           'folk.\n'
                           'Information: Keep every action, target qualifier, value, unit, '
                           'condition, selection rule, and execution order explicit.\n'
                           'Terminology: Allow minor, meaning-preserving wording changes to '
                           'technical terms and operations; retain the exact operation and '
                           'values.\n'
                           'References: Retain all supplied space, device, and person qualifiers, '
                           'even when the layout makes them redundant.\n'
                           'Structure: Use clear requests such as Please, Could you, or Would you '
                           'mind, with complete task details.\n'
                           'Avoid: Excessive formality, apologies, gratitude, optionality such as '
                           'if possible, omitted information, and invented context.\n'
                           '            ',
            'examples': [{'input': 'Tell me the current temperature of the space named Kitchen.',
                          'rewrite': 'Could you tell me the current temperature of the kitchen?'},
                         {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and increase '
                                   'color_temperature by 300.',
                          'rewrite': 'I would like to decrease brightness by 10 and increase color '
                                     'temperature by 300 on dining room lamp 8.'},
                         {'input': "Bring the illuminance in Stairs into line with Kate's saved "
                                   'preference.',
                          'rewrite': "Please bring the stairs' illuminance into line with Kate's "
                                     'preference.'},
                         {'input': 'Compare current noise among Entryway, Laundry Room, Living '
                                   'Room; list every target in the top 2 positions for highest '
                                   'noise.',
                          'rewrite': 'Would you mind comparing the current noise levels in the '
                                     'entryway, laundry room, and living room, then listing the '
                                     'top 2 noisiest rooms?'},
                         {'input': 'Please change all bluetooth speaker devices as follows: adjust '
                                   'playback_content upward by 2 and adjust volume downward by 10. '
                                   'Then tell me the current temperature in Kitchen. Then, for all '
                                   'living_room spaces, work toward this outcome: increase their '
                                   'illuminance by about 100, ending between 780 and 820.',
                          'rewrite': 'Please increase playback content by 2 and decrease volume by '
                                     '10 on all bluetooth speakers. Then tell me the current '
                                     'temperature of the kitchen. After that, for all living '
                                     'rooms, please increase their illuminance by about 100, '
                                     'ending between 780 and 820.'}]},
 'conversational': {'description': '\n'
                                   'Tone: Relaxed everyday dialogue with an assistant, less formal '
                                   'than polite.\n'
                                   'Information: Retain all concrete values, amounts, units, '
                                   'target ranges, top-k counts, requested activities, and action '
                                   'order. Allow limited meaning shifts in everyday wording, but '
                                   'never replace a concrete amount with a vague phrase.\n'
                                   'Terminology: Translate technical properties and operations '
                                   'into familiar expressions, allowing small everyday '
                                   'reinterpretations while keeping their concrete numeric '
                                   'details.\n'
                                   'References: Use the space/device layout to shorten names or '
                                   'omit unnecessary locations and device numbers when the '
                                   'intended target remains clear.\n'
                                   'Structure: Use natural questions, contractions, short '
                                   'lead-ins, and implicit references, expressing the overall '
                                   'request as a person would in conversation.\n'
                                   'Avoid: Forced politeness, omitted numeric details, vague '
                                   'replacements for explicit goals, unrelated new objectives, and '
                                   'invented environment or user-location facts.\n'
                                   '            ',
                    'examples': [{'input': 'Tell me the current temperature of the space named '
                                           'Kitchen.',
                                  'rewrite': 'How hot is the kitchen right now?'},
                                 {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and '
                                           'increase color_temperature by 300. (The dining room '
                                           'contains exactly one lamp, Dining Room Lamp 8. Other '
                                           'rooms may contain lamps.)',
                                  'rewrite': "Let's turn the dining room lamp's brightness down by "
                                             '10 and make its color warmer by 300.'},
                                 {'input': "Bring the illuminance in Stairs into line with Kate's "
                                           'saved preference.',
                                  'rewrite': "Let's bring the stairs' light level to Kate's usual "
                                             'setting.'},
                                 {'input': 'Compare current noise among Entryway, Laundry Room, '
                                           'Living Room; list every target in the top 2 positions '
                                           'for highest noise.',
                                  'rewrite': "Let's compare the noise in the entryway, laundry "
                                             'room, and living room right now. Tell me the top 2 '
                                             'noisiest rooms.'},
                                 {'input': 'Please change all bluetooth speaker devices as '
                                           'follows: adjust playback_content upward by 2 and '
                                           'adjust volume downward by 10. Then tell me the current '
                                           'temperature in Kitchen. Then, for all living_room '
                                           'spaces, work toward this outcome: increase their '
                                           'illuminance by about 100, ending between 780 and 820.',
                                  'rewrite': "Let's move playback content up by 2 and turn the "
                                             'volume down by 10 on all bluetooth speakers. Then '
                                             'tell me the temperature in the kitchen right now. '
                                             "After that, for all living rooms, let's raise the "
                                             'illuminance by about 100 so it ends between 780 and '
                                             '820.'}]},
 'distracting': {'description': '\n'
                                'Tone: Relaxed everyday dialogue with an assistant, following '
                                'conversational style while wandering into unrelated chatter.\n'
                                'Information: Retain all concrete values, amounts, units, target '
                                'ranges, top-k counts, requested activities, dependencies, and '
                                'action order. Allow the same limited everyday meaning shifts as '
                                'conversational, but never replace a concrete amount with a vague '
                                'phrase.\n'
                                'Terminology: Translate technical properties and operations into '
                                'familiar expressions while keeping their concrete numeric '
                                'details.\n'
                                'References: Use the space/device layout to shorten names or omit '
                                'unnecessary locations and device numbers when the intended target '
                                'remains clear.\n'
                                'Structure: Add one or more asides before, between, or after task '
                                "clauses. Vary the topic and placement naturally: today's "
                                "experiences, feelings, tomorrow's plans, personal opinions or "
                                'evaluations, or meaningless filler. Asides may describe the '
                                'current environment, another environment, the device being '
                                'controlled, or other devices. These details may be invented and '
                                "may share the task's topic while remaining irrelevant to what the "
                                'assistant should do.\n'
                                'Avoid: Turning asides into additional requests, changes to task '
                                'targets, conditions, deadlines, or scheduling instructions; '
                                "inventing the user's current location; revealing query answers or "
                                'private memory values; omitting task details. Keep task target '
                                'references grounded in the supplied layout. Removing the asides '
                                'must leave the same conversational request.\n'
                                '            ',
                 'examples': [{'input': 'Tell me the current temperature of the space named '
                                        'Kitchen.',
                               'rewrite': "I spent today tidying this kitchen and still can't "
                                          'decide whether I like its layout. Anyway, how hot is '
                                          'the kitchen right now?'},
                              {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and '
                                        'increase color_temperature by 300.',
                               'layout': 'The dining room contains exactly one lamp, Dining Room '
                                         'Lamp 8. Other rooms may contain lamps.',
                               'rewrite': "The dining room lamp's design reminds me of a hotel I "
                                          "stayed at; that trip always cheers me up. Let's turn "
                                          "the dining room lamp's brightness down by 10 and bump "
                                          'its color temperature up by 300.'},
                              {'input': "Bring the illuminance in Stairs into line with Kate's "
                                        'saved preference.',
                               'rewrite': "Let's bring the stairs' light level to Kate's usual "
                                          "setting. I'm visiting our other office tomorrow; its "
                                          'stairwell always reminds me of my old school.'},
                              {'input': 'Compare current noise among Entryway, Laundry Room, '
                                        'Living Room; list every target in the top 2 positions for '
                                        'highest noise.',
                               'rewrite': "I tried my friend's robot vacuum today. I think its "
                                          "little voice prompts are hilarious. Let's compare the "
                                          'noise in the entryway, laundry room, and living room '
                                          'right now. Tell me the top 2 noisiest rooms.'},
                              {'input': 'Please change all bluetooth speaker devices as follows: '
                                        'adjust playback_content upward by 2 and adjust volume '
                                        'downward by 10. Then tell me the current temperature in '
                                        'Kitchen. Then, for all living_room spaces, work toward '
                                        'this outcome: increase their illuminance by about 100, '
                                        'ending between 780 and 820.',
                               'rewrite': "Let's move playback content up by 2 and turn the volume "
                                          'down by 10 on all bluetooth speakers. The air '
                                          "conditioner at yesterday's cafe looked like a museum "
                                          'piece. Hmm, la-di-da, blah blah. Then tell me the '
                                          'temperature in the kitchen right now. After that, for '
                                          "all living rooms, let's raise the illuminance by about "
                                          '100 so it ends between 780 and 820.'}]},
 'folk': {'description': '\n'
                         '            Tone: Distinctly informal or regional speech, as in a '
                         'conversation with a familiar neighbor; more colloquial than '
                         'conversational.\n'
                         '            Information: Retain all concrete values, amounts, units, '
                         'target ranges, top-k counts, requested activities, and action order. '
                         'Allow limited meaning shifts in everyday wording, but never replace a '
                         'concrete amount with a vague phrase.\n'
                         '            Terminology: Use familiar slang and everyday descriptions of '
                         'technical properties and operations, allowing small meaning shifts while '
                         'keeping their concrete numeric details.\n'
                         '            References: Use the space/device layout to shorten names or '
                         'omit unnecessary locations and device numbers when the intended target '
                         'remains clear.\n'
                         '            Structure: Use contractions, dropped words, and regional '
                         'turns of phrase consistently across the request, with natural local '
                         'equivalents in its language.\n'
                         '            Avoid: Obscure dialect, heavy phonetic spelling, caricature, '
                         'offensive language, omitted numeric details, vague replacements for '
                         'explicit goals, unrelated new objectives, and invented environment '
                         'facts.\n'
                         '            ',
          'examples': [{'input': 'Tell me the current temperature of the space named Kitchen.',
                        'rewrite': "Hey, what's the temperature sittin' at in the kitchen right "
                                   'now?'},
                       {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and increase '
                                 'color_temperature by 300.',
                        'layout': 'The dining room contains exactly one lamp, Dining Room Lamp 8. '
                                  'Other rooms may contain lamps.',
                        'rewrite': 'Knock the brightness down by 10 on the dining room lamp, and '
                                   'crank its color temperature warmer by 300, will ya?'},
                       {'input': "Bring the illuminance in Stairs into line with Kate's saved "
                                 'preference.',
                        'rewrite': "Bring the stairs' light level to the level Kate likes in her "
                                   'saved settings, ya hear?'},
                       {'input': 'Compare current noise among Entryway, Laundry Room, Living Room; '
                                 'list every target in the top 2 positions for highest noise.',
                        'rewrite': 'Outta the entryway, laundry room, and living room, gimme the '
                                   'top 2 noisiest spots right now.'},
                       {'input': 'Please change all bluetooth speaker devices as follows: adjust '
                                 'playback_content upward by 2 and adjust volume downward by 10. '
                                 'Then tell me the current temperature in Kitchen. Then, for all '
                                 'living_room spaces, work toward this outcome: increase their '
                                 'illuminance by about 100, ending between 780 and 820.',
                        'rewrite': 'Skip ahead two tracks on all the bluetooth speakers and knock '
                                   "their volume down by 10. Then gimme the kitchen's temperature "
                                   'right now. After that, bump the light level up by about 100 in '
                                   'every living room so it lands between 780 and 820, will ya?'}]},
 'implicit': {'description': '\n'
                             '            Tone: Indirect, intent-focused requests that leave '
                             'details unstated, using natural everyday language.\n'
                             '            Information: Convey the broad user intent rather than '
                             'every formal constraint. Approximation, omission, ambiguity, and '
                             'some meaning shift are allowed, including qualitative goals instead '
                             'of exact values or ranges.\n'
                             '            Terminology: Reinterpret technical properties and '
                             'operations as a user would describe the desired experience, without '
                             'requiring a literal or numerically equivalent translation.\n'
                             '            References: Ground the request in the space/device '
                             'layout, allowing broader categories, omitted qualifiers, and '
                             'contextual references even when the intended target is implicit '
                             'rather than uniquely specified.\n'
                             '            Structure: Use natural questions, contractions, short '
                             'lead-ins, and implicit references, expressing the overall request as '
                             'a person would in conversation.\n'
                             '            Avoid: Forced politeness, mechanical restatement of '
                             'every parameter, unrelated new objectives, and invented environment '
                             'or user-location facts.\n'
                             '            ',
              'examples': [{'input': 'Tell me the current temperature of the space named Kitchen.',
                            'rewrite': 'How hot is the kitchen right now?'},
                           {'input': 'For Dining Room Lamp 8, decrease brightness by 10 and '
                                     'increase color_temperature by 300. (The dining room contains '
                                     'exactly one lamp, Dining Room Lamp 8. Other rooms may '
                                     'contain lamps.)',
                            'rewrite': "Let's make the dining room lamp a little dimmer and "
                                       'warmer.'},
                           {'input': "Bring the illuminance in Stairs into line with Kate's saved "
                                     'preference.',
                            'rewrite': "Let's get the stair lighting how Kate likes it."},
                           {'input': 'Compare current noise among Entryway, Laundry Room, Living '
                                     'Room; list every target in the top 2 positions for highest '
                                     'noise.',
                            'rewrite': 'Which of the entryway, laundry room, and living room are '
                                       'the noisiest two right now?'},
                           {'input': 'Please change all bluetooth speaker devices as follows: '
                                     'adjust playback_content upward by 2 and adjust volume '
                                     'downward by 10. Then tell me the current temperature in '
                                     'Kitchen. Then, for all living_room spaces, work toward this '
                                     'outcome: increase their illuminance by about 100, ending '
                                     'between 780 and 820.',
                            'rewrite': "Let's skip ahead a couple of tracks and turn the bluetooth "
                                       'speakers down a bit. Then tell me how hot it is in the '
                                       'kitchen. After that, brighten up all the living rooms.'}]}}
