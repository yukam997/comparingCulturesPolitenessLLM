import re
en_find_other_modifier_prompt = """You are analyzing English text to find degree modifiers that are NOT already in a known list.

DEFINITION: A degree modifier is a word or short phrase that scales the intensity of a gradable adjective, adverb, or verb — it answers "to what extent / how much" (e.g., "very good," "barely visible," "completely wrong," "kind of slow"). Do NOT count words which purely fit into one of these other categories of uses:
- as frequency/habituality adverbs (often, rarely, usually, typically, generally, mostly)
- as epistemic/evidential adverbs marking certainty or source of a claim (probably, apparently, obviously, allegedly, supposedly, arguably, definitely, presumably, possibly)
- as evaluative stance adverbs commenting on the whole proposition (surprisingly, worryingly, unfortunately, ideally)
- as plain manner adverbs (quickly, carefully) 

However, please highlight these as degree adverbs if they are functioning as a way to scale the degree of something, even if they can also serve one of the excluded functions elsewhere.

TASK:
1. Read the text below.
2. Identify every word or short phrase functioning as a degree modifier.
3. Exclude any modifier that appears (in any form/case) in the EXCLUSION LIST below.
4. For each remaining (new) modifier found, report: the modifier itself, the word/phrase it modifies, and the exact quote/sentence it appears in.
5. If a modifier is ambiguous (could be degree or something else depending on context), include it but note the ambiguity.
6. If no new modifiers are found, return an empty array — do not force matches.

EXCLUSION LIST (already known — do not report these):
Overly, Excessively, Truly, Barely, Hardly, Scarcely, Just, Merely, Only, A tad, A touch, Marginally, Minimally, Nominally, Mildly, Vaguely, Kind of, Rather, Entirely, Somewhat, Considerably, Substantially, Significantly, Notably, Remarkably, Noticeably, Appreciably, Highly, Incredibly, Extremely, Unbelievably, Very, Exceptionally, Extraordinarily, Unusually, Immensely, Tremendously, Enormously, Hugely, Greatly, Vastly, Completely, Absolutely, Utterly, Totally, Wholly, Fully, Thoroughly, Perfectly, Supremely, Infinitely, Profoundly, Intensely, Strongly, Comparatively, Relatively, Proportionally, Mega, Ultra, So, Real, Way, Way too, Dead, Well, Mad, Hella, Wicked, Bloody, Damn, Freaking, Crazy, Crazily, Measurably, Quantifiably, Reasonably, Moderately, A little, A little bit, A bit, Slightly, Sort of, Kinda, Sorta, A whisker, A smidge, A smidgen, A hair, Faintly, Literally, Positively, Downright, Plain, Monumentally, Staggeringly, Astonishingly, Astoundingly, Phenomenally, Spectacularly, Stunningly, Breathtakingly, Achingly, Quite, Almost, Nearly, Practically, Virtually, Essentially, Basically, Just about, All but, Lil', Awfully, Terribly, Frightfully, Painfully, Deathly, Blindingly, Insanely, Ridiculously, Stupidly, Sick, Proper, Jolly, Fricking, Effing, Goddamn, Seriously, Stupid

TEXT TO ANALYZE:

{text}


OUTPUT FORMAT: Return strict JSON only — a single array containing ONE object per modifier found. If the text contains multiple new modifiers, include all of them as separate objects in the same array; do not merge them or return only one. Example shape with two entries:
[
  {"modifier": "...", "modifies": "...", "context": "...", "ambiguous": true/false},
  {"modifier": "...", "modifies": "...", "context": "...", "ambiguous": true/false}...
]
If exactly one modifier is found, return an array with just that one object. If none are found, return []. Do not include commentary outside the JSON."""

jp_find_other_modifier_prompt = """You are analyzing Japanese text to find degree modifiers (程度副詞) that are NOT already in a known list.

DEFINITION: A degree modifier is a word or short phrase that scales the intensity of a gradable adjective, adverb, or verb — it answers "どのくらい／どの程度" (e.g., "とても嬉しい," "かなり難しい," "ほんの少し"). Do NOT count words which purely fit into one of these other categories of uses:
- as frequency/habituality adverbs (よく, たびたび, いつも, しばしば, 普段, 一般に, たいてい)
- as epistemic/evidential adverbs marking certainty or source of a claim (おそらく, たぶん, どうやら, もちろん, 明らかに, 一応, どうも, きっと, 確かに)
- as evaluative stance adverbs commenting on the whole proposition (残念ながら, 幸い, 意外にも, あいにく, 驚いたことに)
- as plain manner adverbs (急いで, 丁寧に, ゆっくり, 静かに)

However, please highlight these as degree adverbs if they are functioning as a way to scale the degree of something, even if they can also serve one of the excluded functions elsewhere.

TASK:
1. Read the text below.
2. Identify every word or short phrase functioning as a degree modifier (程度副詞).
3. Exclude any modifier that appears (in any form — kanji, hiragana, katakana) in the EXCLUSION LIST below.
4. For each remaining (new) modifier found, report: the modifier itself, the word/phrase it modifies, and the exact quote/sentence it appears in.
5. If a modifier is ambiguous (could be degree or something else depending on context), include it but note the ambiguity.
6. If no new modifiers are found, return an empty array — do not force matches.

EXCLUSION LIST (already known — do not report these):
十分, 多少, 大変, 少し, 相当, 結構, 若干, 非常に, 割と, わりと, やや, とても, とっても, ちょっと, それなり, すごく, 随分, ずいぶん, かなり, いささか, ある程度, あまり, やたら, ちょっぴり, そこそこ, まあまあ, そんなに, それほど, ほぼ, ほんの, しっかり, たっぷり, めちゃ, めっちゃ, ちょー, マジ, まじ, とんでもなく, べらぼうに, よっぽど, 大して, たいして, 概ね, おおむね, 殆ど, ほとんど, 極めて, きわめて, 甚だ, はなはだ, 頗る, すこぶる, 誠に, まことに, 大いに, おおいに, なかなか, 中々, たいそう, 大層, よほど, 余程, 思いのほか, おもいのほか, 案外, あんがい, 意外に, いがいに, 一段と, いちだんと, 一層, いっそう, ますます, 益々, めちゃくちゃ, 滅茶苦茶, ものすごく, 物凄く, とびきり, 飛び切り, 桁違いに, けたちがいに, 抜群に, ばつぐんに, 痛く, いたく, 無茶苦茶, むちゃくちゃ, ひどく, 酷く, 超, ちょう

TEXT TO ANALYZE:

{text}


OUTPUT FORMAT: Return strict JSON only — a single array containing ONE object per modifier found. If the text contains multiple new modifiers, include all of them as separate objects in the same array; do not merge them or return only one. Example shape with two entries:
[
  {"modifier": "...", "modifies": "...", "context": "...", "ambiguous": true/false},
  {"modifier": "...", "modifies": "...", "context": "...", "ambiguous": true/false}...
]
If exactly one modifier is found, return an array with just that one object. If none are found, return []. Do not include commentary outside the JSON."""


check_modifier_prompt = """

Task: In this sentence, judge whether {modifier} is functioning as a modifier of degree.

{sentence}

If it is functioning as a modifier of degree, output the following in JSON format:
{"is_modifier": true, "modifies": "<the word or phrase it modifies>"}
otherwise, output:
{"is_modifier": false, "reason": "<a brief explanation of why it is not a modifier of degree>"}

Output only the raw JSON object above -- no markdown code fences (no ``` or ` characters), no extra commentary, and nothing before or after it. Use double quotes for every key and string value, and lowercase true/false for booleans."""

jp_valence_prompt = """Classify how the modifier {modifier} is being used in the following context:

{sentence}

Choose ONE category that best describes the usage:
- neg_self_mitigate: It mitigates a negative statement about the speaker (e.g., "少し疲れました" softens self-criticism)
- neg_self_emphasize: It emphasizes a negative statement about the speaker (e.g., "すごく遅くなりました" emphasizes self-criticism)
- pos_self_mitigate: It mitigates a positive statement about the speaker (e.g., "私はそれなりに英語ができます" softens what could sound like arrogance)
- pos_self_emphasize: It emphasizes a positive statement about the speaker (e.g., "私はかなり運がいいんです" emphasizes self-praise)
- neg_other_mitigate: It mitigates a negative statement about others (e.g., "あなたの文章は少し読みにくいです" softens criticism)
- neg_other_emphasize: It emphasizes a negative statement about others (e.g., "あなたは非常に面倒くさいですね" emphasizes criticism)
- pos_other_mitigate: It mitigates a positive statement about others (e.g., "あなたはの考えはそれなりに的を射ているようですが、" dampens praise)
- pos_other_emphasize: It emphasizes a positive statement about others (e.g., "あなたは本当に頭がいいですね" emphasizes praise)
- imp_other_mitigate: It mitigates the imposition on others (e.g., "ちょっとしたお願いをしてもいいですか" softens the size of the favor being asked)
- imp_other_emphasize: It emphasizes the imposition on others (e.g., "かなり大きなお願いをしてもいいですか" emphasizes the size of the burden placed on the other person)
- neutral: It does not convey any sentiment toward anyone or towards anything of anyone (e.g., "水が少し冷たいです" is a neutral statement about the water)
- unclear: The usage doesn't fit clearly into any category

Notes: 
- "others" (in neg_other/pos_other/imp_other) is not limited to the direct addressee (the person being spoken to) -- it also includes third parties who are being discussed or referred to (e.g., another editor mentioned in the conversation, someone not present). Criticism or praise directed at such a third party should also be classified as neg_other/pos_other, not as neutral.
- If the hedge appears inside quoted or reported speech (e.g., someone recounting what another person said to them), judge self/other from the perspective of the person who actually uttered those words at the time they were spoken -- not from the perspective of the person currently quoting/reporting it.
- Avoid classifying as neutral whenever possible. Only choose neutral when the usage genuinely does not lean toward any sentiment about anyone; if there is any plausible reading where it conveys or softens/emphasizes a sentiment (toward the speaker, the addressee, a third party, or an imposition), prefer that more specific category instead.

Respond in the form of a json object: {"category": "<category_name>"} (e.g. {"category": "neg_self_mitigate"}). Do not include any other text, explanation, or commentary. Use double quotes for the key and value, and lowercase for the category name."""

en_valence_prompt  = """Classify how the modifier {modifier} is being used in the following context:

{sentence}

Choose ONE category that best describes the usage:
- neg_self_mitigate: It mitigates a negative statement about the speaker (e.g., "I'm a little tired" softens self-pessimism)
- neg_self_emphasize: It emphasizes a negative statement about the speaker (e.g., "I'm really late" emphasizes self-criticism)
- pos_self_mitigate: It mitigates a positive statement about the speaker (e.g., "I think I'm fairly good at english" softens what could sound like arrogance)
- pos_self_emphasize: It emphasizes a positive statement about the speaker (e.g., "I'm very lucky" emphasizes self-praise)
- neg_other_mitigate: It mitigates a negative statement about others (e.g., "You're a little annoying" softens criticism)
- neg_other_emphasize: It emphasizes a negative statement about others (e.g., "You're extremely annoying" emphasizes criticism)
- pos_other_mitigate: It mitigates a positive statement about others (e.g., "You're pretty smart" dampens praise)
- pos_other_emphasize: It emphasizes a positive statement about others (e.g., "You're really smart" emphasizes praise)
- imp_other_mitigate: It mitigates the imposition on others (e.g., "Could I ask you for a small favor?" softens the size of the favor being asked)
- imp_other_emphasize: It emphasizes the imposition on others (e.g., "Could I ask you for quite a big favor?" emphasizes the size of the burden placed on the other person)
- neutral: It does not convey any sentiment toward anyone or towards anything of anyone (e.g., "The water is a bit cold" is a neutral statement about the water)
- unclear: The usage doesn't fit clearly into any category

Notes:
- "others" (in neg_other/pos_other/imp_other) is not limited to the direct addressee (the person being spoken to) -- it also includes third parties who are being discussed or referred to (e.g., another editor mentioned in the conversation, someone not present). Criticism or praise directed at such a third party should also be classified as neg_other/pos_other, not as neutral.
- If the hedge appears inside quoted or reported speech (e.g., someone recounting what another person said to them), judge self/other from the perspective of the person who actually uttered those words at the time they were spoken -- not from the perspective of the person currently quoting/reporting it.
- Avoid classifying as neutral whenever possible. Only choose neutral when the usage genuinely does not lean toward any sentiment about anyone; if there is any plausible reading where it conveys or softens/emphasizes a sentiment (toward the speaker, the addressee, a third party, or an imposition), prefer that more specific category instead.

Respond in the form of a json object: {"category": "<category_name>"} (e.g. {"category": "neg_self_mitigate"}). Do not include any other text, explanation, or commentary. Use double quotes for the key and value, and lowercase for the category name."""

JP_MODIFIER_EXPLANATIONS ={

    'すこし・少し': """Explanation: The word 少し can function both as a modifier of degree ("a little"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 少し待ってください（＝しばらく）
- Example: 少し値上がりした（＝わずかに）
- Non-example: 少しも気にしない（＝「少しも＋否定」で「全く～ない」という呼応表現）""",

    'ちょっと': """Explanation: The word ちょっと can function both as a modifier of degree ("a little/somewhat"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: ちょっと高いですね（＝いくらか、控えめな程度を表す）
- Example: ちょっと分からない（＝少し、少々という意味）
- Non-example: 今日はちょっと…（＝婉曲的な断りを表す語用論的用法で、程度を表していない）
- Non-example: ちょっとしたプレゼントです（＝「ちょっとした＋名詞」で連体修飾）""",

    'それなり': """Explanation: The word それなり can function both as a modifier of degree ("in its own fitting way"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: それなりに頑張った（＝自分の範囲・力なりに、副詞的用法）
- Non-example: それなりの理由がある（＝「それなりの＋名詞」で連体修飾）
- Non-example: 分量はそれなりになる（＝「なる」の補語としての名詞的用法）""",

    'すごく・凄く': """Explanation: The word すごく can function both as a modifier of degree ("very"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: すごく美味しい（＝とても、口語的）
- Non-example: すごく！（＝一語での感嘆表現。間投詞的用法で何も修飾していない）""",

    'ずいぶん・随分': """Explanation: The word 随分 can function both as a modifier of degree ("quite a lot"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 随分と変わったね（＝かなり、驚きを伴う変化）
- Non-example: 随分な言い方だね（＝ひどい・失礼な、「随分な＋名詞」でネガティブな評価的用法）""",

    'かなり': """Explanation: The word かなり can function both as a modifier of degree ("fairly/considerably"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: かなり難しい（＝相当、程度副詞）
- Non-example: かなりの人数が集まった（＝「かなりの＋名詞」で連体修飾的用法）""",

    'いささか・些か': """Explanation: The word いささか can function both as a modifier of degree ("somewhat/slightly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: いささか疑問が残る（＝少し、控えめな不満・懸念）
- Non-example: いささかも動じない（＝「いささかも＋否定」の呼応表現で全否定を強調）""",

    'あるていど・ある程度': """Explanation: The word ある程度 can function both as a modifier of degree ("to some extent"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: ある程度は理解できる（＝一定の範囲で）
- Non-example: ある程度の覚悟が必要だ（＝「ある程度の＋名詞」で連体修飾）""",

    'あまり・余り': """Explanation: The word あまり can function both as a modifier of degree ("not very / to a certain degree"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: あまり好きではない（＝「あまり＋否定」で「それほど～ない」という程度の低さを表す）
- Non-example: あまりにも突然で驚いたので声も出なかった（＝あまりに(も)＋形容詞で「過度に」を表す接続的用法）
- Non-example: 心配のあまり眠れなかった（＝「名詞＋のあまり」で名詞化した用法）""",

    'やたら': """Explanation: The word やたら can function both as a modifier of degree ("excessively"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: やたら忙しい（＝過度に、否定的なニュアンスを伴う程度副詞）
- Non-example: やたらと人に話しかける（＝様態副詞、無差別に・むやみにという行動の仕方を表す）""",

    'ちょっぴり': """Explanation: The word ちょっぴり can function both as a modifier of degree ("just a tiny bit"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: ちょっぴり寂しい（＝ほんの少し、控えめな程度を表す）
- Non-example: ちょっぴりの勇気があれば大丈夫（＝「ちょっぴりの＋名詞」で連体修飾）""",

'たしょう・多少': """Explanation: The word 多少 can function both as a modifier of degree ("a little/somewhat"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 多少疲れた（＝少し）
- Example: 給料が多少上がった（＝わずかに、変化の度合い）
- Non-example: 多少の誤差はある（＝いくらかの、名詞的用法「多少の＋名詞」）
- Non-example: 多少にかかわらず（＝多いか少ないかに関係なく）""",

    'たいへん・大変': """Explanation: The word 大変 can function both as a modifier of degree ("very"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 大変お世話になりました（＝非常に、丁寧な強調）
- Non-example: 本当に大変でした（＝苦労した、困難だった）
- Non-example: 大変な負担をかけている（＝「大変な＋名詞」で連体修飾）""",

    'そうとう・相当': """Explanation: The word 相当 can function both as a modifier of degree ("considerably"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 相当苦労した（＝かなり、副詞）
- Non-example: 10万円ほどに相当する（＝値する、動詞「相当する」）
- Non-example: 相当な実力の持ち主だ（＝「相当な＋名詞」で連体修飾）""",

    'けっこう・結構': """Explanation: The word 結構 can function both as a modifier of degree ("quite/fairly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 結構難しい（＝かなり、程度副詞）
- Non-example: 結構な量の資料（＝かなりの、連体修飾）
- Non-example: お茶はもう結構です（＝十分なので不要、丁寧な断り）
- Non-example: とても結構なお品ですね（＝素晴らしい、褒め言葉）""",

    'じゃっかん・若干': """Explanation: The word 若干 can function both as a modifier of degree ("slightly/a few"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 若干不安が残る（＝少し）
- Example: 若干修正する必要がある（＝少し、わずかに）
- Non-example: 若干名を募集する（＝少々な人数）
- Non-example: 若干の修正が必要だ（＝「若干の＋名詞」で連体修飾）""",

    'ひじょうに・非常に': """Explanation: The word 非常に can function both as a modifier of degree ("extremely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 非常に重要だ（＝とても、フォーマルな場面）
- Example: 非常に困った（＝すごく、困り具合の程度を表す）
- Non-example: 非常に備える（＝緊急事態、「非常」が名詞として使われる用法）""",

    'じゅうぶん・十分': """Explanation: The word 十分 can function both as a modifier of degree ("enough/sufficiently"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 十分に注意する（＝十分に、程度副詞）
- Non-example: 十分な時間がある（＝足りる、名詞的用法「十分な＋名詞」）
- Non-example: テンプレートだけで十分だ（＝それで足りる、それ以上いらない）""",

    'わりと・割と': """Explanation: The word 割と can function both as a modifier of degree ("relatively/fairly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 割と簡単だった（＝思ったより、予想との比較）
- Example: 割と気に入っている（＝そこそこ、控えめな肯定）
- Non-example: 満席率は９割と、非常に混んでいる（＝割合が9割であるという数値を示す）""",

    'やや': """Explanation: The word やや can function both as a modifier of degree ("slightly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: やや値上がりした（＝少し、微妙な変化）
- Example: やや大きめのサイズ（＝若干）
- Non-example: ややこしい話だ（＝複雑だ。副詞「やや」とは語源が異なる形容詞）""",

    'とても': """Explanation: The word とても can function both as a modifier of degree ("very"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: とても嬉しい（＝非常に、素直な肯定）
- Non-example: とても信じられない（＝「とても＋否定」で「到底～ない」という慣用的な否定強調構文）""",

    'とっても': """Explanation: The word とっても can function both as a modifier of degree ("very, casual"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: とっても可愛い（＝「とても」のくだけた強調表現）
- Non-example: 私にとっても大事だよ（＝「に＋とって＋も」で「〜に対しても」を表す別語。副詞の「とても」とは無関係の同形異義）
- Non-example: とっても！（＝一語での感嘆表現。間投詞的用法）""",

    'すこぶる・頗る': """Explanation: The word 頗る can function as a modifier of degree ("extremely"), somewhat literary/formal in register. It has no major competing non-degree function:
- Example: 頗る快調だ（＝非常に、やや古風・文語的）
- Example: 頗る評判がいい（＝とても、フォーマルな響き）""",

    'はなはだ・甚だ': """Explanation: The word 甚だ can function as a modifier of degree ("greatly/very"), typically in formal or written registers. It has no major competing non-degree function:
- Example: 甚だ遺憾である（＝非常に、公式な謝罪・声明の定型表現）
- Example: 甚だ疑問だ（＝大いに、強い疑い）""",

    'まことに・誠に': """Explanation: The word 誠に can function as a modifier of degree ("truly"), used almost exclusively in formal/polite speech. It has no major competing non-degree function:
- Example: 誠に申し訳ございません（＝本当に、フォーマルな謝罪）
- Example: 誠にありがとうございます（＝心から、フォーマルな感謝）""",

    'おおいに・大いに': """Explanation: The word 大いに can function as a modifier of degree ("greatly/very much"). It has no major competing non-degree function:
- Example: 大いに賛成だ（＝強く、明確な同意）
- Example: 大いに楽しんだ（＝十分に、満喫した）""",

    'ほぼ': """Explanation: The word ほぼ can function as a modifier of degree ("almost/nearly"). It has no major competing non-degree function:
- Example: ほぼ完成した（＝もう少しで、完了間近）
- Example: ほぼ全員が参加した（＝大部分）""",

    'おおむね・概ね': """Explanation: The word 概ね can function as a modifier of degree ("generally/roughly"). It has no major competing non-degree function:
- Example: 概ね順調だ（＝大体、全体的な評価）
- Example: 概ね同意見です（＝おおよそ）""",

    'ほとんど・殆ど': """Explanation: The word ほとんど can function both as a modifier of degree ("mostly/almost entirely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: ほとんど終わった（＝大部分）
- Non-example: ほとんど食べない（＝「ほとんど＋否定」で「めったに～ない」という呼応表現）""",

    'ほんの': """Explanation: The word ほんの can function as a modifier of degree ("just/merely"), emphasizing smallness. It has no major competing non-degree function:
- Example: ほんの少しだけ（＝ごくわずかな、小ささの強調）
- Example: ほんの気持ちです（＝ささやかな、贈り物を謙遜して渡す際の定型表現）""",

    'そこそこ': """Explanation: The word そこそこ can function both as a modifier of degree ("fairly/passably"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: そこそこ美味しい（＝まあまあ、控えめな肯定）
- Non-example: 30人そこそこ集まった（＝前後、「数字＋そこそこ」で「およそ」という数量近似用法）""",

    'まあまあ': """Explanation: The word まあまあ can function both as a modifier of degree ("so-so/fairly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: まあまあの出来だ（＝悪くない、可もなく不可もなく）
- Non-example: まあまあ、落ち着いて（＝相手をなだめる間投詞的用法。程度副詞とは別機能）""",

    'そんなに': """Explanation: The word そんなに can function as a modifier of degree ("to that extent"), almost always paired with negation:
- Example: そんなに怒らないで（＝「そんなに＋否定・命令」でその程度まで～するな）
- Example: そんなに難しくない（＝それほど、否定と共に）""",

    'それほど': """Explanation: The word それほど can function both as a modifier of degree ("to that extent"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: それほど難しくない（＝「それほど＋否定」）
- Non-example: それほどでもない（＝褒められた際の謙遜の定型句「大したことはない」という慣用表現）""",

    'たいして・大して': """Explanation: The word 大して can function as a modifier of degree ("not particularly"), almost always paired with negation. It has no major competing non-degree function:
- Example: 大して問題ではない（＝「大して＋否定」でそれほど重要ではない）
- Example: 大して変わらない（＝それほど）""",

    '超・ちょう・ちょー': """Explanation: The word 超 (and its kana forms ちょう/ちょー) can function as a casual/slang modifier of degree ("super/really"). It has no major competing non-degree function in this usage, though ちょう in isolation is a risky string to search for since it's a common homophone (町, 兆, 長, 腸, etc.):
- Example: 超うれしい（＝とても、スラング的強調接頭辞）
- Example: チョーむかつく（＝非常に、カタカナ表記で若者言葉のニュアンス）""",

    'めっちゃ・めちゃ': """Explanation: The words めちゃ/めっちゃ can function as casual/slang modifiers of degree ("super/really"), used identically in speech to intensify an adjective or adverb. They have no major competing non-degree function:
- Example: めっちゃ美味しい（＝超、くだけたスラング）
- Example: めちゃ怒られた（＝ひどく、程度の強調）""",

    'めちゃくちゃ・滅茶苦茶': """Explanation: The word めちゃくちゃ can function both as a modifier of degree ("extremely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: めちゃくちゃ忙しい（＝非常に、程度副詞）
- Non-example: 部屋がめちゃくちゃだ（＝散らかっている、元々の意味「無茶苦茶」で状態を表す形容動詞的用法）""",

    'むちゃくちゃ・無茶苦茶': """Explanation: The word むちゃくちゃ can function both as a modifier of degree ("extremely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 無茶苦茶忙しい（＝非常に、程度副詞）
- Non-example: 部屋が無茶苦茶だ（＝めちゃめちゃ、散らかっている・元々の意味）""",

    'ひどく・酷く': """Explanation: The word ひどく can function both as a modifier of degree ("severely/very"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: ひどく落ち込んでいる（＝非常に、程度）
- Non-example: ひどく扱われた（＝残酷に、元々の意味「乱暴に」という様態の用法）""",

    'まじ・マジ': """Explanation: The word まじ/マジ can function both as a modifier of degree ("really/very", slang), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: まじ疲れた（＝本当に、形容詞の前で副詞的に）
- Non-example: マジで！？（＝本当に！？、驚きを表す間投詞的用法）
- Non-example: マジな話（＝真剣な、「マジな＋名詞」で連体修飾）""",

    'あんがい・案外': """Explanation: The word 案外 can function as a modifier of degree/expectation-mismatch ("unexpectedly"), typically qualifying an evaluation relative to what was expected. It has no major competing non-degree function:
- Example: 案外簡単だった（＝予想に反して、意外にも簡単だった）
- Example: 案外美味しい（＝思ったより）""",

    'いがいに・意外に': """Explanation: The word 意外に can function both as a modifier of degree/expectation-mismatch ("unexpectedly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 意外に難しい（＝思ったより、予想外に）
- Non-example: 意外な結果だった（＝「意外な＋名詞」で連体修飾）""",

    'おもいのほか・思いのほか': """Explanation: The word 思いのほか can function as a modifier of degree/expectation-mismatch ("more than expected"). It has no major competing non-degree function:
- Example: 思いのほか時間がかかった（＝予想以上に）
- Example: 思いのほか上手くいった（＝案外）""",

    'いくら・幾ら': """Explanation: The word いくら can function as a modifier of degree in the pattern "いくら～ても/でも" ("no matter how much"), but also functions as a simple quantity question word ("how much"). These are some examples and non-examples of its use as a modifier of degree:
- Example: いくら頑張っても報われない（＝どんなに、程度の強調を伴う逆接構文）
- Non-example: これはいくらですか（＝値段を尋ねる疑問詞、程度の意味なし）""",

    'いちだんと・一段と': """Explanation: The word いちだんと can function as a modifier of degree ("even more/a step further"), marking an increase relative to a previous state. It has no major competing non-degree function:
- Example: いちだんと美しくなった（＝さらに、以前より一段階上の程度）""",

    'いっそう・一層': """Explanation: The word いっそう can function as a modifier of degree ("all the more/even more so"). It has no major competing non-degree function:
- Example: いっそう努力する必要がある（＝さらに、より一層）""",

    'いちばん・一番': """Explanation: The word いちばん can function both as a modifier of degree (superlative, "most"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: これがいちばん好きだ（＝最も、程度の最上級を表す）
- Non-example: 一番を目指す（＝1位、順位を表す名詞的用法）""",

    'いっさい・一切': """Explanation: The word いっさい can function as a modifier of degree/totality ("entirely/at all"), almost always paired with negation. It has no major competing non-degree function:
- Example: 一切関係ない（＝「一切＋否定」で全く～ない）""",

    'いろいろ・色々': """Explanation: The word いろいろ functions as a modifier of variety/degree of diversity ("various"), rather than intensity per se, but is often grouped with degree-adjacent words since it scales "how much variety." It has no major competing non-degree function:
- Example: いろいろ考えた（＝様々に、多角的に）""",

    'いろいろと・色々と': """Explanation: The word いろいろと functions similarly to いろいろ, marking degree/extent of variety in an action. It has no major competing non-degree function:
- Example: いろいろとお世話になりました（＝様々な面で、丁寧な表現）""",

    'おおきく・大きく': """Explanation: The word おおきく can function both as a modifier of degree ("greatly/significantly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 大きく変わった（＝著しく、程度の大きさを表す）
- Non-example: 大きく育った子供（＝物理的なサイズの形容詞的用法）""",

    'おおはばに・大幅に': """Explanation: The word 大幅に can function as a modifier of degree ("substantially/by a large margin"). It has no major competing non-degree function:
- Example: 大幅に改善した（＝著しく、大きな幅で）""",

    'おもに・主に': """Explanation: The word おもに functions as a modifier of proportion/degree ("mainly/primarily"), scaling how much of something applies. It has no major competing non-degree function:
- Example: 主に日本語で書かれている（＝大部分は、中心的に）""",

    'かんぜんに・完全に': """Explanation: The word 完全に can function both as a modifier of degree ("completely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 完全に理解した（＝すっかり、程度の最大値）
- Non-example: 完全な計画だ（＝欠点のない、「完全な＋名詞」で連体修飾）""",

    'きょくりょく・極力': """Explanation: The word 極力 can function as a modifier of degree ("as much as possible"), typically preceding an effort-related verb. It has no major competing non-degree function:
- Example: 極力早く対応します（＝できるだけ、最大限の努力を示す）""",

    'きわめて・極めて': """Explanation: The word きわめて can function as a modifier of degree ("extremely"), formal register. It has no major competing non-degree function:
- Example: 極めて重要な問題だ（＝非常に、フォーマルな強調）""",

    'けたちがいに・桁違いに': """Explanation: The word 桁違いに can function as a modifier of degree ("by an order of magnitude"), emphasizing an extreme, disproportionate difference. It has no major competing non-degree function:
- Example: 桁違いに大きい（＝比べ物にならないほど、程度の飛躍を表す）""",

    'げんに・厳に': """Explanation: The word 厳に can function as a modifier of degree/strictness ("strictly"), typically preceding prohibition-related verbs in formal writing. It has no major competing non-degree function:
- Example: 厳に慎むべきだ（＝厳しく、強く戒める表現）""",

    'これいじょう・これ以上': """Explanation: The word これ以上 can function as a modifier of degree ("any further/more than this"), typically marking a limit being reached. It has no major competing non-degree function:
- Example: これ以上待てない（＝これより多く・さらに、限界を示す）""",

    'さらに・更に': """Explanation: The word さらに can function as a modifier of degree ("further/even more"), marking an addition to an already-established degree. It has no major competing non-degree function:
- Example: さらに難しくなった（＝もっと、程度の追加的な上昇）""",

    'しょうしょう・少々': """Explanation: The word 少々 can function both as a modifier of degree ("a little"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 少々お待ちください（＝少し、丁寧な表現）
- Non-example: 少々の問題（＝いくらかの、「少々の＋名詞」で連体修飾）""",

    'すくなくとも・少なくとも': """Explanation: The word 少なくとも can function as a modifier of degree/minimum threshold ("at least"). It has no major competing non-degree function:
- Example: 少なくとも3回は確認した（＝最低限、下限を示す程度表現）""",

    'すべて・全て': """Explanation: The word すべて functions as a modifier of totality/degree ("entirely/all"), rather than a pure quantity modifier scaling "how much." It has no major competing non-degree function in this usage:
- Example: すべて理解した（＝完全に、全体を対象とする程度表現）""",

    'ぜったいに・絶対に': """Explanation: The word 絶対に can function both as a modifier of degree/certainty ("absolutely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 絶対に成功させる（＝必ず、確信の程度を最大化する表現）
- Non-example: 絶対の自信がある（＝「絶対の＋名詞」で連体修飾）""",

    'ぜんぜん・全然': """Explanation: The word 全然 can function both as a modifier of degree ("not at all" with negation, or colloquially "totally" without negation), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 全然おいしくない（＝「全然＋否定」でまったく～ない）
- Example: 全然大丈夫（＝口語的に「全く」の意味で肯定文に使う新しい用法）""",

    'たいそう・大層': """Explanation: The word たいそう can function as a modifier of degree ("very/greatly"), somewhat old-fashioned register. It has no major competing non-degree function:
- Example: たいそう喜んでいた（＝非常に、やや古風な表現）""",

    'たくさん・沢山': """Explanation: The word たくさん can function both as a modifier of degree/quantity ("a lot"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: たくさん食べた（＝多く、量の程度を表す）
- Non-example: もうたくさんだ（＝十分だ、うんざりしたという慣用表現）""",

    'つよく・強く': """Explanation: The word つよく can function both as a modifier of degree ("strongly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 強く希望する（＝程度を強調する副詞的用法）
- Non-example: 強く殴った（＝力を込めて、物理的な力の様態を表す）""",

    'できるだけ・出来るだけ': """Explanation: The word できるだけ can function as a modifier of degree ("as much as possible"). It has no major competing non-degree function:
- Example: できるだけ早く来てください（＝可能な限り、最大限の程度を求める表現）""",

    'とくに・特に': """Explanation: The word とくに can function as a modifier of degree/emphasis ("especially/particularly"), highlighting a case that exceeds the general degree. It has no major competing non-degree function:
- Example: 特に難しい問題だ（＝とりわけ、程度の際立ちを示す）""",

    'とびきり・飛び切り': """Explanation: The word とびきり can function as a modifier of degree ("exceptionally"), emphasizing that something stands out from the norm. It has no major competing non-degree function:
- Example: とびきり美味しい（＝格別に、際立った程度を表す）""",

    'なかなか・中々': """Explanation: The word なかなか can function both as a modifier of degree ("quite/considerably"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: なかなか面白い（＝かなり、予想以上の評価を伴う程度表現）
- Non-example: なかなか終わらない（＝「なかなか＋否定」で「簡単には～ない」という呼応表現）""",

    'なにも・何も': """Explanation: The word 何も can function as a modifier of degree/totality ("nothing at all"), almost always paired with negation. It has no major competing non-degree function:
- Example: 何も知らない（＝「何も＋否定」で全く知らないという程度の強調）""",

    'はげしく・激しく': """Explanation: The word はげしく can function both as a modifier of degree ("intensely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 激しく後悔している（＝非常に、感情の程度を強調）
- Non-example: 激しく雨が降る（＝勢いよく、様態を表す用法）""",

    'ばつぐんに・抜群に': """Explanation: The word 抜群に can function as a modifier of degree ("outstandingly"), marking a quality that surpasses the norm. It has no major competing non-degree function:
- Example: 抜群に良い成績（＝際立って、極めて高い程度を表す）""",

    'ひろく・広く': """Explanation: The word ひろく can function both as a modifier of degree/scope ("widely"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 広く知られている（＝一般的に、範囲の広さを表す程度表現）
- Non-example: 広く部屋を使う（＝物理的な広さの形容詞的用法）""",

    'ふかく・深く': """Explanation: The word ふかく can function both as a modifier of degree ("deeply"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 深く感謝する（＝心から、程度の強調表現）
- Non-example: 深く掘る（＝物理的な深さの様態を表す用法）""",

    'ほんとに・本当に': """Explanation: The word 本当に can function both as a modifier of degree ("really/very"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 本当に嬉しい（＝とても、心からの強調）
- Non-example: それは本当ですか（＝真実かどうかを問う、真偽判断の用法）""",

    'ますます・益々': """Explanation: The word ますます can function as a modifier of degree ("increasingly/more and more"), marking a progression in intensity. It has no major competing non-degree function:
- Example: ますます人気が高まっている（＝いっそう、程度の増加を表す）""",

    'まったく・全く': """Explanation: The word まったく can function both as a modifier of degree ("completely" or, with negation, "not at all"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: まったく同感だ（＝完全に、程度の最大化）
- Example: まったく分からない（＝「全く＋否定」で「全然～ない」）
- Non-example: まったく、しょうがないなあ（＝呆れを表す間投詞的用法）""",

    'もうすこし・もう少し': """Explanation: The word もう少し can function as a modifier of degree ("a bit more"), marking a small additional increment. It has no major competing non-degree function:
- Example: もう少し待ってください（＝あと少し、追加的な程度を表す）""",

    'もっとも・最も': """Explanation: The word もっとも can function both as a modifier of degree (superlative, "most"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: 最も重要な点だ（＝一番、最上級の程度表現）
- Non-example: もっとも、それには例外がある（＝逆接・留保を示す接続詞的用法「ただし」）""",

    'ものすごく・物凄く': """Explanation: The word ものすごく can function as a modifier of degree ("tremendously"). It has no major competing non-degree function:
- Example: ものすごく疲れた（＝非常に、程度の強い強調）""",

    'よく・良く': """Explanation: The word よく can function both as a modifier of degree ("well/thoroughly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: よく考えてから決める（＝十分に、程度の強調）
- Non-example: よく公園に行く（＝頻度を表す「しばしば」という頻度副詞的用法）""",

    'よほど・余程': """Explanation: The word よほど can function as a modifier of degree ("to a considerable extent"), often implying something beyond the ordinary. It has no major competing non-degree function:
- Example: よほど疲れていたようだ（＝相当、程度の強い推測を伴う）""",

    'ごく': """Explanation: The word ごく can function as a modifier of degree ("extremely/quite"), typically preceding another degree word or adjective to intensify smallness or ordinariness. It has no major competing non-degree function:
- Example: ごく普通の生活（＝きわめて、程度の強調）
- Example: ごく僅かな差（＝ほんの、微小さの強調）""",

    'しっかり': """Explanation: The word しっかり can function both as a modifier of degree ("firmly/thoroughly"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: しっかり勉強する（＝十分に、程度の強調）
- Non-example: しっかりしてください（＝気をしっかり持て、という心構えを促す慣用的命令表現）""",

    'そこまで': """Explanation: The word そこまで can function as a modifier of degree ("to that extent"), typically implying the degree is surprising or excessive. It has no major competing non-degree function:
- Example: そこまで気にしなくていい（＝それほど、程度の強調）""",

    'たっぷり': """Explanation: The word たっぷり can function as a modifier of degree/quantity ("plentifully"). It has no major competing non-degree function:
- Example: たっぷり時間がある（＝十分すぎるほど、量の豊富さを表す）""",

    'とんでもなく': """Explanation: The word とんでもなく can function as a modifier of degree ("outrageously/incredibly"). It has no major competing non-degree function:
- Example: とんでもなく難しい（＝桁違いに、程度の極端さを表す）""",

    'どうしても': """Explanation: The word どうしても can function as a modifier of degree/necessity ("no matter what/absolutely"), typically marking an unshakeable degree of intent or difficulty. It has no major competing non-degree function:
- Example: どうしても諦められない（＝何としても、強い程度の決意）""",

    'どうも': """Explanation: The word どうも can function both as a modifier of degree ("somehow/rather", hedging a judgment), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: どうも様子がおかしい（＝なんとなく、程度の曖昧な強調）
- Non-example: どうも、ありがとうございます（＝挨拶・感謝を表す定型的な間投詞的用法）""",

    'なるべく': """Explanation: The word なるべく can function as a modifier of degree ("as much as possible"). It has no major competing non-degree function:
- Example: なるべく早く終わらせたい（＝できるだけ、最大限の程度を求める表現）""",

    'べらぼうに': """Explanation: The word べらぼうに can function as a modifier of degree ("absurdly/outrageously"), colloquial register. It has no major competing non-degree function:
- Example: べらぼうに高い（＝とんでもなく、程度の極端さを強調する俗語的表現）""",

    'まだまだ': """Explanation: The word まだまだ can function as a modifier of degree ("still a long way off/not nearly enough"), marking an insufficient degree relative to some standard. It has no major competing non-degree function:
- Example: まだまだ実力不足だ（＝全然足りない、程度の不十分さを強調）""",

    'もっと': """Explanation: The word もっと can function as a modifier of degree ("more"), marking a comparative increase. It has no major competing non-degree function:
- Example: もっと頑張ろう（＝これ以上、程度の上昇を求める表現）""",

    'よっぽど': """Explanation: The word よっぽど can function as a modifier of degree ("to quite an extent"), colloquial variant of よほど, often implying surprise. It has no major competing non-degree function:
- Example: よっぽど嬉しかったんだね（＝相当、程度の強い推測）""",

    'より': """Explanation: The word より can function as a modifier of degree in comparative constructions ("more/-er"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: より良い結果を目指す（＝もっと、比較の程度を示す）
- Non-example: 東京より大阪の方が近い（＝比較の基準点を示す格助詞的用法、程度そのものは表さない）""",

'いたく・痛く': """Explanation: The word いたく can function both as a modifier of degree ("keenly/deeply", formal register), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:
- Example: いたく感動した（＝深く、心を強く動かされた程度を表す）
- Example: いたく感激している（＝非常に、フォーマルな強調）
- Non-example: 転んで足が痛くなった（＝形容詞「痛い」の連用形で、身体的な痛みそのものを表す用法。程度副詞のいたくとは同形異義）""",

    'いちじるしく・著しく': """Explanation: The word いちじるしく can function as a modifier of degree ("remarkably/markedly"), emphasizing that a change or difference is large enough to be conspicuous. It has no major competing non-degree function:
- Example: 業績が著しく改善した（＝大幅に、変化の程度を強調する表現）
- Example: 著しく異なる結果となった（＝際立って、差の程度を強調する表現）""",

    'ちょっとした': """Explanation: The word ちょっとした functions as an attributive (連体修飾) modifier of a following noun ("a slight/casual X"), scaling down how significant or noteworthy that noun is — but unlike ちょっと itself, it cannot modify a verb or adjective directly, so it does not function as a degree adverb in the usual sense. These are some examples of its attributive scaling function and a non-example showing the boundary with ちょっと:
- Example: ちょっとしたプレゼントです（＝ささやかな、大げさではないという程度を表す連体修飾）
- Example: ちょっとした問題が起きた（＝軽微な、深刻ではない程度を表す連体修飾）
- Non-example: ちょっと問題が起きた（＝ここでの「ちょっと」は「問題が起きた」という動詞句全体を修飾する副詞的用法で、ちょっとしたとは文法的機能が異なる）""",

}
EN_MODIFIER_EXPLANATIONS = {
    "a little": "Explanation: The phrase \"a little\" can function both as a modifier of degree (\"slightly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: She was a little tired after the trip. (= slightly)\n- Non-example: He lives in a little house by the lake. (= small; \"little\" here is a literal size adjective modifying \"house,\" not scaling the degree of another word)\n- Non-example: He only ate a little before leaving. (= a small amount; functions as a noun phrase/quantity pronoun, not modifying an adjective or verb)",
    "a bit": "Explanation: The phrase \"a bit\" can function both as a modifier of degree (\"slightly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This is a bit expensive. (= slightly)\n- Non-example: Can I have a bit of that cake? (= a small piece/amount; functions as a quantity noun phrase, not modifying an adjective directly)",
    "a hair": "Explanation: These phrases can all function as modifiers of degree (\"just a tiny bit\"), used interchangeably to soften a gradable adjective or adverb. They can also function as literal quantity noun phrases referring to a small physical amount, rather than scaling degree:\n- Example: The soup needs a tad more salt. (= slightly)\n- Example: She was a touch nervous before the interview. (= slightly)\n- Non-example: Cut off just a hair of the ribbon. (= a small physical piece/length; a literal quantity noun phrase, not modifying an adjective or verb)",
    "a smidge": "Explanation: These phrases can all function as modifiers of degree (\"just a tiny bit\"), used interchangeably to soften a gradable adjective or adverb. They can also function as literal quantity noun phrases referring to a small physical amount, rather than scaling degree:\n- Example: The soup needs a tad more salt. (= slightly)\n- Example: She was a touch nervous before the interview. (= slightly)\n- Non-example: Cut off just a hair of the ribbon. (= a small physical piece/length; a literal quantity noun phrase, not modifying an adjective or verb)",
    "a smidgen": "Explanation: These phrases can all function as modifiers of degree (\"just a tiny bit\"), used interchangeably to soften a gradable adjective or adverb. They can also function as literal quantity noun phrases referring to a small physical amount, rather than scaling degree:\n- Example: The soup needs a tad more salt. (= slightly)\n- Example: She was a touch nervous before the interview. (= slightly)\n- Non-example: Cut off just a hair of the ribbon. (= a small physical piece/length; a literal quantity noun phrase, not modifying an adjective or verb)",
    "a tad": "Explanation: These phrases can all function as modifiers of degree (\"just a tiny bit\"), used interchangeably to soften a gradable adjective or adverb. They can also function as literal quantity noun phrases referring to a small physical amount, rather than scaling degree:\n- Example: The soup needs a tad more salt. (= slightly)\n- Example: She was a touch nervous before the interview. (= slightly)\n- Non-example: Cut off just a hair of the ribbon. (= a small physical piece/length; a literal quantity noun phrase, not modifying an adjective or verb)",
    "a touch": "Explanation: These phrases can all function as modifiers of degree (\"just a tiny bit\"), used interchangeably to soften a gradable adjective or adverb. They can also function as literal quantity noun phrases referring to a small physical amount, rather than scaling degree:\n- Example: The soup needs a tad more salt. (= slightly)\n- Example: She was a touch nervous before the interview. (= slightly)\n- Non-example: Cut off just a hair of the ribbon. (= a small physical piece/length; a literal quantity noun phrase, not modifying an adjective or verb)",
    "a whisker": "Explanation: These phrases can all function as modifiers of degree (\"just a tiny bit\"), used interchangeably to soften a gradable adjective or adverb. They can also function as literal quantity noun phrases referring to a small physical amount, rather than scaling degree:\n- Example: The soup needs a tad more salt. (= slightly)\n- Example: She was a touch nervous before the interview. (= slightly)\n- Non-example: Cut off just a hair of the ribbon. (= a small physical piece/length; a literal quantity noun phrase, not modifying an adjective or verb)",
    "kind of": "Explanation: The phrase \"kind of\" can function both as a modifier of degree (\"somewhat\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I'm kind of hungry right now. (= somewhat)\n- Non-example: What kind of music do you like? (= type/category; asking about classification, not degree)",
    "kinda": "Explanation: The word \"kinda\" is the casual/contracted spelling of \"kind of\" and functions identically as a modifier of degree (\"somewhat\"):\n- Example: I'm kinda tired today. (= somewhat)",
    "sort of": "Explanation: The phrase \"sort of\" can function both as a modifier of degree (\"somewhat\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I'm sort of confused about the instructions. (= somewhat)\n- Non-example: What sort of person would say that? (= type/category; asking about classification, not degree)",
    "sorta": "Explanation: The word \"sorta\" is the casual/contracted spelling of \"sort of\" and functions identically as a modifier of degree (\"somewhat\"):\n- Example: It's sorta hard to explain. (= somewhat)",
    "somewhat": "Explanation: The word \"somewhat\" can function as a modifier of degree (\"to some extent\"). It is a fairly unambiguous degree adverb with no major competing non-degree function:\n- Example: The results were somewhat disappointing. (= to some extent)\n- Example: He was somewhat surprised by the outcome. (= moderately)",
    "rather": "Explanation: The word \"rather\" can function both as a modifier of degree (\"quite/somewhat\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: It's rather cold outside today. (= quite/somewhat)\n- Non-example: I would rather stay home tonight. (= a preference marker in \"would rather,\" not a degree modifier)\n- Non-example: I chose tea rather than coffee. (= a comparative/contrastive conjunction meaning \"instead of,\" not a degree modifier)",
    "pretty": "Explanation: The word \"pretty\" can function both as a modifier of degree (\"quite/fairly\", casual), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That movie was pretty good. (= quite/fairly)\n- Non-example: She wore a pretty dress to the party. (= attractive/beautiful; a literal descriptive adjective, not a degree modifier)",
    "quite": "Explanation: The word \"quite\" can function as a modifier of degree, but its degree reading itself varies: it can mean \"fairly/moderately\" or, especially in British English, \"completely/entirely.\" These are some examples of its use as a modifier of degree:\n- Example: The book was quite interesting. (= fairly/moderately)\n- Example: I'm quite finished with the report. (= completely; a stronger degree reading, especially in British English)",
    "relatively": "Explanation: The word \"relatively\" can function as a modifier of degree (\"comparatively\"). It is a fairly unambiguous degree adverb with no major competing non-degree function:\n- Example: The neighborhood is relatively quiet at night. (= comparatively)\n- Example: The exam was relatively easy compared to last year's. (= in comparison to a standard)",
    "comparatively": "Explanation: The word \"comparatively\" can function as a modifier of degree (\"relatively speaking\"), nearly identical in usage to \"relatively.\" It has no major competing non-degree function:\n- Example: Sales were comparatively strong this quarter. (= relatively, when set against a benchmark)",
    "moderately": "Explanation: The word \"moderately\" can function as a modifier of degree (\"to a middling extent\"). It is a fairly unambiguous degree adverb with no major competing non-degree function:\n- Example: The company was moderately successful last quarter. (= to a middling extent)",
    "reasonably": "Explanation: The word \"reasonably\" can function both as a modifier of degree (\"fairly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The hotel was reasonably priced. (= fairly)\n- Non-example: He behaved reasonably during the negotiation. (= sensibly/rationally; describes the manner of behaving, not degree)",
    "really": "Explanation: The word \"really\" can function both as a modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This cake is really delicious. (= very)\n- Non-example: Did that really happen, or did you make it up? (= truly/in fact; asserts the truth of the proposition rather than scaling a gradable property)\n- Non-example: Really? I had no idea. (= a standalone interjection expressing surprise, not modifying any word)",
    "very": "Explanation: The word \"very\" can function both as a modifier of degree (\"to a high extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: She was very happy with the results. (= to a high extent)\n- Non-example: You are the very person I was looking for. (= exact/same, as in \"the very same day\"; an emphatic adjective modifying a noun directly, not a degree adverb)",
    "extremely": "Explanation: The word \"extremely\" can function as a modifier of degree (\"to a very high degree\"). It is a fairly unambiguous degree adverb with no major competing non-degree function:\n- Example: The exam was extremely difficult. (= to a very high degree)",
    "absolutely": "Explanation: The word \"absolutely\" can function both as a modifier of degree (\"completely/utterly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The performance was absolutely stunning. (= completely, maximal degree)\n- Non-example: \"Are you coming?\" \"Absolutely.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "achingly": "Explanation: The word \"achingly\" can function as a modifier of degree (\"intensely\"), typically preceding an adjective describing beauty, slowness, or longing. It has no major competing non-degree function in this usage:\n- Example: The scenery was achingly beautiful. (= intensely)",
    "adequately": "Explanation: The word \"adequately\" can function as a modifier of degree (\"sufficiently\"). It has no major competing non-degree function:\n- Example: The team was adequately prepared for the exam. (= sufficiently)",
    "all but": "Explanation: The phrase \"all but\" can function as a modifier of degree (\"almost entirely\"), typically preceding a verb or adjective to indicate a near-complete state. It has no major competing non-degree function in this usage:\n- Example: The old bridge was all but destroyed by the storm. (= almost completely)",
    "almost": "Explanation: These words can all function as modifiers of degree (\"very close to, but not quite\"), marking that a state or event is nearly but not fully reached. \"Practically\" additionally has a competing manner-adverb function:\n- Example: The tank was almost empty. (= very close to)\n- Example: She was nearly finished with the report. (= very close to)\n- Non-example: He handled the crisis practically, without panicking. (= in a practical/pragmatic manner; a manner adverb describing how he acted, not a degree modifier)",
    "nearly": "Explanation: These words can all function as modifiers of degree (\"very close to, but not quite\"), marking that a state or event is nearly but not fully reached. \"Practically\" additionally has a competing manner-adverb function:\n- Example: The tank was almost empty. (= very close to)\n- Example: She was nearly finished with the report. (= very close to)\n- Non-example: He handled the crisis practically, without panicking. (= in a practical/pragmatic manner; a manner adverb describing how he acted, not a degree modifier)",
    "practically": "Explanation: These words can all function as modifiers of degree (\"very close to, but not quite\"), marking that a state or event is nearly but not fully reached. \"Practically\" additionally has a competing manner-adverb function:\n- Example: The tank was almost empty. (= very close to)\n- Example: She was nearly finished with the report. (= very close to)\n- Non-example: He handled the crisis practically, without panicking. (= in a practical/pragmatic manner; a manner adverb describing how he acted, not a degree modifier)",
    "virtually": "Explanation: These words can all function as modifiers of degree (\"very close to, but not quite\"), marking that a state or event is nearly but not fully reached. \"Practically\" additionally has a competing manner-adverb function:\n- Example: The tank was almost empty. (= very close to)\n- Example: She was nearly finished with the report. (= very close to)\n- Non-example: He handled the crisis practically, without panicking. (= in a practical/pragmatic manner; a manner adverb describing how he acted, not a degree modifier)",
    "just about": "Explanation: These words can all function as modifiers of degree (\"very close to, but not quite\"), marking that a state or event is nearly but not fully reached. \"Practically\" additionally has a competing manner-adverb function:\n- Example: The tank was almost empty. (= very close to)\n- Example: She was nearly finished with the report. (= very close to)\n- Non-example: He handled the crisis practically, without panicking. (= in a practical/pragmatic manner; a manner adverb describing how he acted, not a degree modifier)",
    "appreciably": "Explanation: The word \"appreciably\" can function as a modifier of degree (\"noticeably/to a measurable extent\"). It has no major competing non-degree function:\n- Example: Prices rose appreciably last quarter. (= noticeably)",
    "astonishingly": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "astoundingly": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "staggeringly": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "phenomenally": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "spectacularly": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "stunningly": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "breathtakingly": "Explanation: These words can all function as modifiers of degree (\"to a remarkable/extreme extent\"), each emphasizing that a quality is far beyond the ordinary. They have no major competing non-degree function in this usage:\n- Example: The results were astonishingly good. (= remarkably)\n- Example: The building failed spectacularly. (= dramatically, to an extreme degree)\n- Example: The view was breathtakingly beautiful. (= extremely)",
    "at all": "Explanation: The phrase \"at all\" can function as a modifier of degree (\"to any extent\"), almost always paired with negation or a question to emphasize a total absence or query the presence of a quality. It has no major competing non-degree function:\n- Example: I don't like this movie at all. (= not to any extent)\n- Example: Is this bothering you at all? (= to any extent)",
    "awfully": "Explanation: The word \"awfully\" can function both as a casual modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That's awfully kind of you. (= very)\n- Non-example: The team played awfully in the second half. (= badly; describes the quality of the performance itself, not scaling another word's degree)",
    "barely": "Explanation: These words can all function as modifiers of degree marking a very low/minimal degree (\"almost not at all\"), typically implying something barely crosses a threshold. They have no major competing non-degree function in this usage:\n- Example: I could barely hear the announcement. (= almost not at all)\n- Example: She hardly noticed the change. (= almost not at all)\n- Example: There was scarcely enough food for everyone. (= almost not enough)",
    "hardly": "Explanation: These words can all function as modifiers of degree marking a very low/minimal degree (\"almost not at all\"), typically implying something barely crosses a threshold. They have no major competing non-degree function in this usage:\n- Example: I could barely hear the announcement. (= almost not at all)\n- Example: She hardly noticed the change. (= almost not at all)\n- Example: There was scarcely enough food for everyone. (= almost not enough)",
    "scarcely": "Explanation: These words can all function as modifiers of degree marking a very low/minimal degree (\"almost not at all\"), typically implying something barely crosses a threshold. They have no major competing non-degree function in this usage:\n- Example: I could barely hear the announcement. (= almost not at all)\n- Example: She hardly noticed the change. (= almost not at all)\n- Example: There was scarcely enough food for everyone. (= almost not enough)",
    "basically": "Explanation: The word \"basically\" can function as a modifier of degree/approximation (\"essentially, in the main\"), rather than scaling intensity per se — it marks that a simplified or core-level characterization applies. It has no major competing non-degree function:\n- Example: The two plans are basically the same. (= essentially)",
    "blindingly": "Explanation: The word \"blindingly\" can function as a modifier of degree (\"extremely\"), typically preceding \"obvious\" or \"fast.\" It has no major competing non-degree function in this usage:\n- Example: The answer was blindingly obvious. (= extremely)",
    "bloody": "Explanation: These words can all function as vulgar/slang modifiers of degree (\"very\"), used to intensify an adjective or adverb, most common in British/informal English. They have no major competing non-degree function in this usage:\n- Example: That's a bloody good idea. (= very)\n- Example: This is a damn good movie. (= very)\n- Example: That's a freaking huge house. (= very)",
    "damn": "Explanation: These words can all function as vulgar/slang modifiers of degree (\"very\"), used to intensify an adjective or adverb, most common in British/informal English. They have no major competing non-degree function in this usage:\n- Example: That's a bloody good idea. (= very)\n- Example: This is a damn good movie. (= very)\n- Example: That's a freaking huge house. (= very)",
    "freaking": "Explanation: These words can all function as vulgar/slang modifiers of degree (\"very\"), used to intensify an adjective or adverb, most common in British/informal English. They have no major competing non-degree function in this usage:\n- Example: That's a bloody good idea. (= very)\n- Example: This is a damn good movie. (= very)\n- Example: That's a freaking huge house. (= very)",
    "fricking": "Explanation: These words can all function as vulgar/slang modifiers of degree (\"very\"), used to intensify an adjective or adverb, most common in British/informal English. They have no major competing non-degree function in this usage:\n- Example: That's a bloody good idea. (= very)\n- Example: This is a damn good movie. (= very)\n- Example: That's a freaking huge house. (= very)",
    "effing": "Explanation: These words can all function as vulgar/slang modifiers of degree (\"very\"), used to intensify an adjective or adverb, most common in British/informal English. They have no major competing non-degree function in this usage:\n- Example: That's a bloody good idea. (= very)\n- Example: This is a damn good movie. (= very)\n- Example: That's a freaking huge house. (= very)",
    "goddamn": "Explanation: These words can all function as vulgar/slang modifiers of degree (\"very\"), used to intensify an adjective or adverb, most common in British/informal English. They have no major competing non-degree function in this usage:\n- Example: That's a bloody good idea. (= very)\n- Example: This is a damn good movie. (= very)\n- Example: That's a freaking huge house. (= very)",
    "closely": "Explanation: The word \"closely\" can function both as a modifier of degree (\"to a great extent,\" e.g. of resemblance), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The two proposals closely resemble each other. (= to a great extent)\n- Non-example: The guard watched the door closely. (= attentively/near at hand; a manner/spatial adverb describing how the watching was done, not scaling degree)",
    "considerably": "Explanation: The word \"considerably\" can function as a modifier of degree (\"to a large extent\"). It has no major competing non-degree function:\n- Example: Prices increased considerably this year. (= to a large extent)",
    "crazy": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "crazily": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "insanely": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "ridiculously": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "stupidly": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "stupid": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "sick": "Explanation: These words can all function as casual modifiers of degree (\"extremely\"), but each also has a literal, non-degree adjectival meaning (mentally unstable, unintelligent, physically ill). These are some examples and non-examples of their use as a modifier of degree:\n- Example: This traffic is crazy bad today. (= extremely)\n- Example: That's an insanely good deal. (= extremely)\n- Non-example: He acted crazy after losing his job. (= mentally unstable/erratic; a literal descriptive adjective, not a degree modifier)\n- Non-example: She's been sick all week. (= physically ill; a literal descriptive adjective, not a degree modifier)",
    "dead": "Explanation: The word \"dead\" can function both as a casual modifier of degree (\"completely\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I'm dead tired after that workout. (= completely)\n- Non-example: They found the body dead at the scene. (= literally deceased; a literal descriptive adjective, not a degree modifier)",
    "deathly": "Explanation: The word \"deathly\" can function as a modifier of degree (\"extremely\"), typically preceding \"pale,\" \"quiet,\" or \"afraid.\" It has no major competing non-degree function in this usage:\n- Example: The room went deathly quiet. (= extremely)",
    "directly": "Explanation: The word \"directly\" can function both as a modifier of degree (in comparative/proportional expressions), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The results are directly proportional to the input. (= exactly, to a precise degree)\n- Non-example: Please speak to me directly, not through an intermediary. (= without an intermediary; a manner adverb describing how the communication happens, not scaling degree)",
    "downright": "Explanation: The word \"downright\" can function as a modifier of degree (\"thoroughly/completely\"), typically intensifying a negative adjective. It has no major competing non-degree function:\n- Example: That comment was downright rude. (= thoroughly)",
    "enormously": "Explanation: The word \"enormously\" can function as a modifier of degree (\"to a huge extent\"). It has no major competing non-degree function:\n- Example: The policy change enormously affected small businesses. (= to a huge extent)",
    "enough": "Explanation: The word \"enough\" can function both as a modifier of degree (\"to a sufficient extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The coffee isn't hot enough. (= to a sufficient extent)\n- Non-example: We don't have enough chairs for everyone. (= a sufficient quantity/number; a quantity determiner modifying a noun, not scaling an adjective or adverb)",
    "completely": "Explanation: These words can all function as modifiers of degree (\"to the fullest possible extent\"), used largely interchangeably to indicate a maximal degree. \"Totally\" additionally has a standalone interjection use:\n- Example: I completely agree with you. (= to the fullest extent)\n- Example: The building was utterly destroyed. (= to the fullest extent)\n- Non-example: \"Should we go?\" \"Totally.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "entirely": "Explanation: These words can all function as modifiers of degree (\"to the fullest possible extent\"), used largely interchangeably to indicate a maximal degree. \"Totally\" additionally has a standalone interjection use:\n- Example: I completely agree with you. (= to the fullest extent)\n- Example: The building was utterly destroyed. (= to the fullest extent)\n- Non-example: \"Should we go?\" \"Totally.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "fully": "Explanation: These words can all function as modifiers of degree (\"to the fullest possible extent\"), used largely interchangeably to indicate a maximal degree. \"Totally\" additionally has a standalone interjection use:\n- Example: I completely agree with you. (= to the fullest extent)\n- Example: The building was utterly destroyed. (= to the fullest extent)\n- Non-example: \"Should we go?\" \"Totally.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "totally": "Explanation: These words can all function as modifiers of degree (\"to the fullest possible extent\"), used largely interchangeably to indicate a maximal degree. \"Totally\" additionally has a standalone interjection use:\n- Example: I completely agree with you. (= to the fullest extent)\n- Example: The building was utterly destroyed. (= to the fullest extent)\n- Non-example: \"Should we go?\" \"Totally.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "utterly": "Explanation: These words can all function as modifiers of degree (\"to the fullest possible extent\"), used largely interchangeably to indicate a maximal degree. \"Totally\" additionally has a standalone interjection use:\n- Example: I completely agree with you. (= to the fullest extent)\n- Example: The building was utterly destroyed. (= to the fullest extent)\n- Non-example: \"Should we go?\" \"Totally.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "wholly": "Explanation: These words can all function as modifiers of degree (\"to the fullest possible extent\"), used largely interchangeably to indicate a maximal degree. \"Totally\" additionally has a standalone interjection use:\n- Example: I completely agree with you. (= to the fullest extent)\n- Example: The building was utterly destroyed. (= to the fullest extent)\n- Non-example: \"Should we go?\" \"Totally.\" (= a standalone affirmative interjection meaning \"yes, definitely,\" not modifying any word)",
    "especially": "Explanation: The word \"especially\" can function as a modifier of degree (\"to an unusually high extent\"), marking that a case exceeds the general degree. It has no major competing non-degree function:\n- Example: The exam was especially difficult this year. (= particularly, to a heightened degree)",
    "essentially": "Explanation: The word \"essentially\" can function as a modifier of degree/approximation (\"in essence, basically\"), similar to \"basically.\" It has no major competing non-degree function:\n- Example: The two arguments are essentially identical. (= in essence)",
    "exceptionally": "Explanation: The word \"exceptionally\" can function as a modifier of degree (\"to an unusually high extent\"). It has no major competing non-degree function:\n- Example: She is an exceptionally talented musician. (= to an unusually high extent)",
    "excessively": "Explanation: The word \"excessively\" can function as a modifier of degree (\"to an unreasonably high extent\"). It has no major competing non-degree function:\n- Example: The report was excessively long. (= to an unreasonably high extent)",
    "exclusively": "Explanation: The word \"exclusively\" can function as a modifier of degree/restriction (\"solely, to the exclusion of all else\"). It has no major competing non-degree function:\n- Example: This offer is available exclusively to members. (= solely)",
    "extraordinarily": "Explanation: The word \"extraordinarily\" can function as a modifier of degree (\"to a remarkable extent\"). It has no major competing non-degree function:\n- Example: The team performed extraordinarily well. (= to a remarkable extent)",
    "faintly": "Explanation: The word \"faintly\" can function both as a modifier of degree (\"slightly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: She was faintly amused by the joke. (= slightly)\n- Non-example: The room was faintly lit by a single candle. (= dimly; describes the literal weakness of light, borderline between manner and degree but typically treated as a manner/intensity-of-light description rather than scaling an abstract quality)",
    "fundamentally": "Explanation: The word \"fundamentally\" can function as a modifier of degree (\"at the most basic/core level\"). It has no major competing non-degree function:\n- Example: The two proposals are fundamentally different. (= at the core level)",
    "further": "Explanation: The word \"further\" can function both as a modifier of degree (\"to a greater extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This further complicates the situation. (= to a greater extent)\n- Non-example: We drove further down the road. (= a greater physical distance; a spatial adverb, not a degree modifier)",
    "genuinely": "Explanation: The word \"genuinely\" can function as a modifier of degree (\"truly/sincerely\"), scaling how authentically a state applies. It has no major competing non-degree function:\n- Example: I'm genuinely excited about this project. (= truly)",
    "greatly": "Explanation: The word \"greatly\" can function as a modifier of degree (\"to a large extent\"). It has no major competing non-degree function:\n- Example: The new policy greatly improved efficiency. (= to a large extent)",
    "hella": "Explanation: These words can all function as casual/slang modifiers of degree (\"very\"), regionally flavored intensifiers used identically to scale an adjective or adverb. They have no major competing non-degree function in this usage:\n- Example: That concert was hella fun. (= very)\n- Example: This phone is mega expensive. (= very)\n- Example: That's a wicked good idea. (= very, British/New England slang)",
    "mega": "Explanation: These words can all function as casual/slang modifiers of degree (\"very\"), regionally flavored intensifiers used identically to scale an adjective or adverb. They have no major competing non-degree function in this usage:\n- Example: That concert was hella fun. (= very)\n- Example: This phone is mega expensive. (= very)\n- Example: That's a wicked good idea. (= very, British/New England slang)",
    "ultra": "Explanation: These words can all function as casual/slang modifiers of degree (\"very\"), regionally flavored intensifiers used identically to scale an adjective or adverb. They have no major competing non-degree function in this usage:\n- Example: That concert was hella fun. (= very)\n- Example: This phone is mega expensive. (= very)\n- Example: That's a wicked good idea. (= very, British/New England slang)",
    "wicked": "Explanation: These words can all function as casual/slang modifiers of degree (\"very\"), regionally flavored intensifiers used identically to scale an adjective or adverb. They have no major competing non-degree function in this usage:\n- Example: That concert was hella fun. (= very)\n- Example: This phone is mega expensive. (= very)\n- Example: That's a wicked good idea. (= very, British/New England slang)",
    "highly": "Explanation: The word \"highly\" can function as a modifier of degree (\"to a high extent\"). It has no major competing non-degree function:\n- Example: This is a highly unusual situation. (= to a high extent)",
    "hugely": "Explanation: The word \"hugely\" can function as a modifier of degree (\"to a huge extent\"). It has no major competing non-degree function:\n- Example: The film was hugely successful. (= to a huge extent)",
    "immensely": "Explanation: The word \"immensely\" can function as a modifier of degree (\"to an immense extent\"). It has no major competing non-degree function:\n- Example: I immensely enjoyed the concert. (= to an immense extent)",
    "in any way": "Explanation: The phrase \"in any way\" can function as a modifier of degree (\"to any extent\"), almost always paired with negation to emphasize total absence of an effect. It has no major competing non-degree function:\n- Example: This decision doesn't affect you in any way. (= to any extent)",
    "in detail": "Explanation: The phrase \"in detail\" can function as a modifier of degree/thoroughness (\"thoroughly, leaving nothing out\"). It has no major competing non-degree function:\n- Example: Please explain your reasoning in detail. (= thoroughly)",
    "in full": "Explanation: The phrase \"in full\" can function as a modifier of degree (\"completely\"), typically with verbs like \"pay\" or \"repay.\" It has no major competing non-degree function:\n- Example: The invoice must be paid in full. (= completely)",
    "incredibly": "Explanation: The word \"incredibly\" can function both as a modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The food was incredibly good. (= very)\n- Non-example: Incredibly, he survived the fall unharmed. (= a sentence-initial stance adverb meaning \"unbelievably\" commenting on the whole proposition, not scaling a gradable adjective)",
    "infinitely": "Explanation: The word \"infinitely\" can function as a hyperbolic modifier of degree (\"to an enormous extent\"), typically with comparatives. It has no major competing non-degree function in this usage:\n- Example: This version is infinitely better than the last one. (= to an enormous extent)",
    "intensely": "Explanation: The word \"intensely\" can function as a modifier of degree (\"to a strong extent\"). It has no major competing non-degree function:\n- Example: She was intensely focused on the task. (= to a strong extent)",
    "jolly": "Explanation: The word \"jolly\" can function both as a modifier of degree (\"very\", chiefly British), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That's jolly good news! (= very, British informal)\n- Non-example: He's always in a jolly mood. (= cheerful/happy; a literal descriptive adjective, not a degree modifier)",
    "just": "Explanation: The word \"just\" can function both as a modifier of degree (\"exactly/simply\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The soup is just right. (= exactly)\n- Non-example: She just arrived a moment ago. (= a temporal adverb meaning \"very recently,\" not a degree modifier)\n- Non-example: I was just kidding. (= a restrictive/minimizing marker meaning \"only,\" bordering on degree but typically classed as a focus particle rather than scaling a gradable property)",
    "less than": "Explanation: The phrase \"less than\" can function as a modifier of degree (\"not fully/insufficiently\"), typically preceding an adjective to indicate falling short of a standard. It has no major competing non-degree function in this usage:\n- Example: The service was less than satisfactory. (= not fully, falling short)",
    "lil'": "Explanation: The word \"lil'\" is a casual spelling of \"little,\" and can function as a modifier of degree/size (\"small\"), but also have other functions similar to \"a little.\" These are some examples and non-examples of its use as a modifier of degree:\n- Example: Just gimme a lil' more time. (= a little)\n- Non-example: That's my lil' brother. (= young/small in age; a literal descriptive adjective, not a degree modifier)",
    "literally": "Explanation: The word \"literally\" can function both as a casual intensifier of degree (\"very\", used hyperbolically/figuratively), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I'm literally dying of laughter. (= figuratively \"very much,\" despite the word's literal meaning)\n- Non-example: He literally translated the phrase word for word. (= in a literal, non-figurative manner; describes exactness of meaning/translation, not scaling degree)",
    "mad": "Explanation: The word \"mad\" can function both as a casual/slang modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That's mad expensive. (= very, slang)\n- Non-example: She was mad at her brother. (= angry; a literal descriptive adjective, not a degree modifier)",
    "marginally": "Explanation: The word \"marginally\" can function as a modifier of degree (\"only slightly\"). It has no major competing non-degree function:\n- Example: The new model is marginally faster. (= only slightly)",
    "measurably": "Explanation: The word \"measurably\" can function as a modifier of degree (\"to a quantifiable extent\"). It has no major competing non-degree function:\n- Example: Performance improved measurably after the update. (= to a quantifiable extent)",
    "merely": "Explanation: The word \"merely\" can function as a modifier of degree/restriction (\"only, to a minimal extent\"), downplaying the significance of something. It has no major competing non-degree function:\n- Example: It was merely a suggestion, not an order. (= only)",
    "mildly": "Explanation: The word \"mildly\" can function as a modifier of degree (\"to a small extent\"). It has no major competing non-degree function:\n- Example: I was mildly annoyed by the delay. (= to a small extent)",
    "minimally": "Explanation: The word \"minimally\" can function as a modifier of degree (\"to the smallest extent\"). It has no major competing non-degree function:\n- Example: The design was minimally changed from last year. (= to the smallest extent)",
    "monumentally": "Explanation: The word \"monumentally\" can function as a modifier of degree (\"extremely\"), typically intensifying a negative adjective. It has no major competing non-degree function:\n- Example: That was a monumentally bad decision. (= extremely)",
    "more": "Explanation: The word \"more\" can function both as a comparative modifier of degree (\"to a greater extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This version is more reliable than the last. (= to a greater extent, comparative)\n- Non-example: I need more chairs for the meeting. (= a greater quantity/number; a quantity determiner modifying a noun, not scaling an adjective or adverb)",
    "most": "Explanation: The word \"most\" can function both as a superlative modifier of degree (\"to the greatest extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This is the most difficult exam I've taken. (= to the greatest extent, superlative)\n- Non-example: Most people agreed with the plan. (= the majority of; a quantity determiner modifying a noun, not scaling an adjective or adverb)",
    "the most": "Explanation: The phrase \"the most\" functions as the superlative modifier of degree (\"to the greatest extent\"), the definite counterpart of \"most\":\n- Example: This is the most exciting news I've heard all year. (= to the greatest extent)",
    "much": "Explanation: The word \"much\" can function both as a modifier of degree (with comparatives, \"to a great extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This is much better than before. (= to a great extent, intensifying the comparative)\n- Non-example: How much water do we need? (= a quantity question word, not modifying an adjective or adverb)",
    "nominally": "Explanation: The word \"nominally\" can function as a modifier of degree (\"only in name, to a minimal/technical extent\"). It has no major competing non-degree function:\n- Example: He is nominally in charge, but she makes all the decisions. (= in name only, minimal actual degree)",
    "notably": "Explanation: These words can both function as modifiers of degree (\"to a degree that is noticeable\"). They have no major competing non-degree function:\n- Example: Sales were notably higher this quarter. (= to a noticeable extent)\n- Example: The room was noticeably colder after the window broke. (= to a noticeable extent)",
    "noticeably": "Explanation: These words can both function as modifiers of degree (\"to a degree that is noticeable\"). They have no major competing non-degree function:\n- Example: Sales were notably higher this quarter. (= to a noticeable extent)\n- Example: The room was noticeably colder after the window broke. (= to a noticeable extent)",
    "only": "Explanation: The word \"only\" can function as a modifier of degree/restriction (\"merely, to a limited extent\"), downplaying scope or significance. It has no major competing non-degree function in this usage:\n- Example: It was only a minor issue. (= merely, to a limited extent)",
    "overly": "Explanation: The word \"overly\" can function as a modifier of degree (\"excessively\"). It has no major competing non-degree function:\n- Example: He was overly cautious about the investment. (= excessively)",
    "painfully": "Explanation: The word \"painfully\" can function both as a modifier of degree (\"extremely,\" often for something unfortunate/awkward), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The truth was painfully obvious. (= extremely)\n- Non-example: She was painfully injured in the accident. (= in a manner causing pain; describes the physical injury itself, not scaling an abstract quality)",
    "perfectly": "Explanation: The word \"perfectly\" can function both as a modifier of degree (\"completely\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That's perfectly reasonable. (= completely)\n- Non-example: She sang the song perfectly. (= without flaw; describes the quality/manner of the performance itself, not scaling another word's degree)",
    "plain": "Explanation: The word \"plain\" can function both as a modifier of degree (\"simply/completely,\" informal), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That's just plain wrong. (= simply/completely)\n- Non-example: She wore a plain dress. (= unadorned/simple in appearance; a literal descriptive adjective, not a degree modifier)",
    "poorly": "Explanation: The word \"poorly\" can function both as a modifier of degree (\"to a low degree\", when paired with a scalar past participle, parallel to how \"well\" marks the high end of the same scale), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The risks of the treatment are poorly understood. (= understood to a low degree, parallel to \"well understood\" at the high end of the same scale)\n- Example: The building was poorly insulated. (= insulated to a low degree)\n- Non-example: The team played poorly in the final. (= badly; describes the quality of the performance itself, not scaling a separate gradable property)",
    "positively": "Explanation: The word \"positively\" can function both as a modifier of degree (\"truly/absolutely\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The audience was positively thrilled. (= truly/absolutely)\n- Non-example: She responded positively to the treatment. (= favorably; describes the nature/direction of the response, not scaling degree)",
    "profoundly": "Explanation: The word \"profoundly\" can function as a modifier of degree (\"deeply/to a great extent\"). It has no major competing non-degree function:\n- Example: The experience profoundly changed her outlook. (= deeply)",
    "proper": "Explanation: The word \"proper\" can function both as a modifier of degree (\"thoroughly/really,\" British informal), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That was a proper mess. (= thoroughly, British informal)\n- Non-example: Please use the proper tool for this job. (= correct/appropriate; a literal descriptive adjective, not a degree modifier)",
    "proportionally": "Explanation: The word \"proportionally\" can function as a modifier of degree (\"in proportion to something else\"). It has no major competing non-degree function:\n- Example: Costs increased proportionally with demand. (= in proportion, scaling degree relative to another factor)",
    "quantifiably": "Explanation: The word \"quantifiably\" can function as a modifier of degree (\"to a measurable extent\"). It has no major competing non-degree function:\n- Example: The new process is quantifiably more efficient. (= to a measurable extent)",
    "remarkably": "Explanation: The word \"remarkably\" can function as a modifier of degree (\"to a strikingly high extent\"). It has no major competing non-degree function:\n- Example: She remained remarkably calm during the crisis. (= to a strikingly high extent)",
    "seriously": "Explanation: The word \"seriously\" can function both as a casual modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This is seriously annoying. (= very)\n- Non-example: We need to talk seriously about the budget. (= in a serious/solemn manner; describes how the talking is done, not scaling degree)",
    "significantly": "Explanation: The word \"significantly\" can function as a modifier of degree (\"to a considerable extent\"). It has no major competing non-degree function:\n- Example: Revenue increased significantly this year. (= to a considerable extent)",
    "simply": "Explanation: The word \"simply\" can function both as a modifier of degree (\"absolutely/completely\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: The view was simply breathtaking. (= absolutely)\n- Non-example: Please explain it simply, without jargon. (= in a simple/uncomplicated manner; describes how the explaining is done, not scaling degree)",
    "slightly": "Explanation: The word \"slightly\" can function as a modifier of degree (\"a little\"). It is a fairly unambiguous degree adverb with no major competing non-degree function:\n- Example: The room was slightly warmer than usual. (= a little)\n- Example: She slightly adjusted her plan. (= made a small change in degree/extent)",
    "so": "Explanation: The word \"so\" can function both as a modifier of degree (\"to such an extent\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I'm so tired today. (= to a high extent)\n- Non-example: It started raining, so we went inside. (= a conjunction meaning \"therefore,\" not a degree modifier)\n- Non-example: She likes it, and so do I. (= a pro-form/agreement marker meaning \"likewise,\" not a degree modifier)",
    "strictly": "Explanation: The word \"strictly\" can function both as a modifier of degree (\"absolutely/completely\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This area is strictly off-limits. (= absolutely)\n- Non-example: Strictly speaking, that's not quite accurate. (= a sentence-level hedge marking precision of framing, not scaling a gradable property)",
    "strongly": "Explanation: The word \"strongly\" can function both as a modifier of degree (\"intensely\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I strongly recommend this book. (= intensely)\n- Non-example: The bridge was strongly built to withstand earthquakes. (= sturdily; describes the physical manner of construction, not scaling an abstract quality)",
    "substantially": "Explanation: The word \"substantially\" can function as a modifier of degree (\"to a large extent\"). It has no major competing non-degree function:\n- Example: Costs were substantially reduced after the merger. (= to a large extent)",
    "sufficiently": "Explanation: The word \"sufficiently\" can function as a modifier of degree (\"enough, to an adequate extent\"). It has no major competing non-degree function:\n- Example: The bridge was sufficiently reinforced before winter. (= to an adequate extent)",
    "supremely": "Explanation: The word \"supremely\" can function as a modifier of degree (\"to the highest possible extent\"). It has no major competing non-degree function:\n- Example: She was supremely confident going into the match. (= to the highest extent)",
    "terribly": "Explanation: The word \"terribly\" can function both as a modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I'm terribly sorry for the inconvenience. (= very)\n- Non-example: The team played terribly in the final. (= badly; describes the quality of the performance itself, not scaling another word's degree)",
    "thoroughly": "Explanation: The word \"thoroughly\" can function as a modifier of degree (\"completely/exhaustively\"). It has no major competing non-degree function:\n- Example: I thoroughly enjoyed the film. (= completely)",
    "too": "Explanation: The word \"too\" can function both as a modifier of degree (\"excessively\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This coffee is too hot to drink. (= excessively)\n- Non-example: I'd like to come too. (= \"also\"; an additive focus particle, not a degree modifier)",
    "way too": "Explanation: The phrase \"way too\" can function as a modifier of degree, an emphatic/casual intensification of \"too\" (\"excessively, by a large margin\"). It has no major competing non-degree function:\n- Example: This shirt is way too small for me. (= excessively, more emphatically than plain \"too\")",
    "tremendously": "Explanation: The word \"tremendously\" can function as a modifier of degree (\"to a huge extent\"). It has no major competing non-degree function:\n- Example: The new policy tremendously improved morale. (= to a huge extent)",
    "truly": "Explanation: The word \"truly\" can function both as a modifier of degree (\"very\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This is a truly remarkable achievement. (= very)\n- Non-example: Yours truly, John. (= a sincerity marker in a formal letter closing, not a degree modifier)",
    "unbelievably": "Explanation: The word \"unbelievably\" can function as a modifier of degree (\"to an extreme, hard-to-believe extent\"). It has no major competing non-degree function in this usage:\n- Example: The concert was unbelievably good. (= extremely)",
    "unduly": "Explanation: The word \"unduly\" can function as a modifier of degree (\"excessively, more than is warranted\"). It has no major competing non-degree function:\n- Example: She was unduly worried about the exam. (= excessively)",
    "unsalvageably": "Explanation: The word \"unsalvageably\" can function as a modifier of degree (\"to a point beyond repair/recovery\"). It has no major competing non-degree function:\n- Example: The document was unsalvageably corrupted. (= to a point beyond repair)",
    "unusually": "Explanation: The word \"unusually\" can function as a modifier of degree (\"to an atypically high/low extent\"). It has no major competing non-degree function:\n- Example: It was unusually warm for October. (= to an atypically high extent)",
    "vaguely": "Explanation: The word \"vaguely\" can function both as a modifier of degree (\"slightly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: I was vaguely aware of the issue. (= slightly)\n- Non-example: The instructions were vaguely worded. (= imprecisely; describes the manner of wording, not scaling degree)",
    "vastly": "Explanation: The word \"vastly\" can function as a modifier of degree (\"to a huge extent\"), typically with comparatives. It has no major competing non-degree function:\n- Example: This version is vastly superior to the last. (= to a huge extent)",
    "way": "Explanation: The word \"way\" can function both as a casual modifier of degree (\"much,\" intensifying comparatives), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: This is way better than the old version. (= much, casual intensifier)\n- Non-example: Which way should we go? (= direction; a literal noun, not a degree modifier)",
    "well": "Explanation: The word \"well\" can function both as a modifier of degree (\"thoroughly,\" especially before past participles like \"well aware\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: She is well aware of the risks. (= thoroughly)\n- Non-example: He plays the piano well. (= skillfully; describes the manner/quality of the playing, not scaling a separate gradable adjective)",
    "a little bit": "Explanation: The phrase \"a little\" can function both as a modifier of degree (\"slightly\"), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: She was a little tired after the trip. (= slightly)\n- Non-example: He lives in a little house by the lake. (= small; \"little\" here is a literal size adjective modifying \"house,\" not scaling the degree of another word)\n- Non-example: He only ate a little before leaving. (= a small amount; functions as a noun phrase/quantity pronoun, not modifying an adjective or verb)",
    "frightfully": "Explanation: The word \"frightfully\" can function as a modifier of degree (\"very\", chiefly British), similar to \"terribly\" or \"awfully\" in this usage. It has no major competing non-degree function:\n- Example: I'm frightfully sorry about the mix-up. (= very)",
    "real": "Explanation: The word \"real\" can function both as a casual modifier of degree (\"very\", nonstandard/dialectal), but also have other functions. These are some examples and non-examples of its use as a modifier of degree:\n- Example: That's real nice of you. (= very, informal/dialectal)\n- Non-example: Is this a real diamond? (= genuine/authentic; a literal descriptive adjective, not a degree modifier)"
}
EN_ALL_MODIFIER_WORDS = {
    "a bit", "a hair", "a little", "a little bit", "a smidge", "a smidgen", "a tad",
    "a touch", "a whisker", "absolutely", "achingly", "adequately", "all but", "almost",
    "appreciably", "astonishingly", "astoundingly", "at all", "awfully", "barely",
    "basically", "blindingly", "bloody", "breathtakingly", "closely", "comparatively",
    "completely", "considerably", "crazily", "crazy", "damn", "dead", "deathly",
    "directly", "downright", "effing", "enormously", "enough", "entirely", "especially",
    "essentially", "exceptionally", "excessively", "exclusively", "extraordinarily",
    "extremely", "faintly", "freaking", "fricking", "frightfully", "fully",
    "fundamentally", "further", "genuinely", "goddamn", "greatly", "hardly", "hella",
    "highly", "hugely", "immensely", "in any way", "in detail", "in full", "incredibly",
    "indefinitely", "infinitely", "insanely", "intensely", "jolly", "just", "just about",
    "kind of", "kinda", "less than", "lil'", "literally", "mad", "marginally",
    "measurably", "mega", "merely", "mildly", "minimally", "moderately", "monumentally",
    "more", "most", "much", "nearly", "nominally", "notably", "noticeably", "only",
    "overly", "painfully", "perfectly", "phenomenally", "plain", "poorly", "positively",
    "practically", "profoundly", "proper", "proportionally", "quantifiably", "quite",
    "rather", "real", "really", "reasonably", "relatively", "remarkably", "ridiculously",
    "scarcely", "seriously", "sick", "significantly", "simply", "slightly", "so",
    "somewhat", "sort of", "sorta", "spectacularly", "staggeringly", "strictly",
    "strongly", "stunningly", "stupid", "stupidly", "substantially", "sufficiently",
    "supremely", "terribly", "the most", "thoroughly", "too", "totally", "tremendously",
    "truly", "ultra", "unbelievably", "unduly", "unsalvageably", "unusually", "utterly",
    "vaguely", "vastly", "very", "virtually", "way", "way too", "well", "wholly", "wicked",
}
JP_ALL_MODIFIER_WORDS = {
    "あまり", "あるていど", "ある程度", "あんがい", "いがいに", "いくら", "いささか",
    "いたく", "いちじるしく", "いちだんと", "いちばん", "いっさい", "いっそう", "いろいろ",
    "いろいろと", "おおいに", "おおきく", "おおはばに", "おおむね", "おもいのほか",
    "おもに", "かなり", "かんぜんに", "きょくりょく", "きわめて", "けたちがいに", "けっこう",
    "げんに", "これいじょう", "これ以上", "ごく", "さらに", "しっかり", "しょうしょう",
    "じゃっかん", "じゅうぶん", "すくなくとも", "すこし", "すこぶる", "すごく", "すべて",
    "ずいぶん", "ぜったいに", "ぜんぜん", "そうとう", "そこそこ", "そこまで", "それなり",
    "それほど", "そんなに", "たいして", "たいそう", "たいへん", "たくさん", "たしょう",
    "たっぷり", "ちょう", "ちょっと", "ちょっとした", "ちょっぴり", "ちょー", "つよく",
    "できるだけ", "とくに", "とっても", "とても", "とびきり", "とんでもなく", "どうしても",
    "どうも", "なかなか", "なにも", "なるべく", "はげしく", "はなはだ", "ばつぐんに",
    "ひじょうに", "ひどく", "ひろく", "ふかく", "べらぼうに", "ほとんど", "ほぼ", "ほんとに",
    "ほんの", "まあまあ", "まことに", "まじ", "ますます", "まだまだ", "まったく",
    "むちゃくちゃ", "めちゃ", "めちゃくちゃ", "めっちゃ", "もうすこし", "もう少し", "もっと",
    "もっとも", "ものすごく", "やたら", "やや", "よく", "よっぽど", "よほど", "より",
    "わりと", "マジ", "一切", "一層", "一段と", "一番", "中々", "主に", "些か", "何も",
    "余り", "余程", "全く", "全て", "全然", "凄く", "出来るだけ", "割と", "十分", "厳に",
    "多少", "大いに", "大きく", "大して", "大変", "大層", "大幅に", "完全に", "少々",
    "少し", "少なくとも", "幾ら", "広く", "強く", "思いのほか", "意外に", "抜群に", "更に",
    "最も", "本当に", "桁違いに", "案外", "極めて", "極力", "概ね", "殆ど", "沢山", "深く",
    "滅茶苦茶", "激しく", "無茶苦茶", "物凄く", "特に", "甚だ", "痛く", "益々", "相当",
    "結構", "絶対に", "良く", "色々", "色々と", "若干", "著しく", "誠に", "超", "酷く",
    "随分", "非常に", "頗る", "飛び切り",
}
JP_MODIFIER_GROUPS = {
    "あまり": "あまり・余り", "余り": "あまり・余り",
    "あるていど": "あるていど・ある程度", "ある程度": "あるていど・ある程度",
    "あんがい": "あんがい・案外", "案外": "あんがい・案外",
    "いがいに": "いがいに・意外に", "意外に": "いがいに・意外に",
    "いくら": "いくら・幾ら", "幾ら": "いくら・幾ら",
    "いささか": "いささか・些か", "些か": "いささか・些か",
    "いたく": "いたく・痛く", "痛く": "いたく・痛く",
    "いちじるしく": "いちじるしく・著しく", "著しく": "いちじるしく・著しく",
    "いちだんと": "いちだんと・一段と", "一段と": "いちだんと・一段と",
    "いちばん": "いちばん・一番", "一番": "いちばん・一番",
    "いっさい": "いっさい・一切", "一切": "いっさい・一切",
    "いっそう": "いっそう・一層", "一層": "いっそう・一層",
    "いろいろ": "いろいろ・色々", "色々": "いろいろ・色々",
    "いろいろと": "いろいろと・色々と", "色々と": "いろいろと・色々と",
    "おおいに": "おおいに・大いに", "大いに": "おおいに・大いに",
    "おおきく": "おおきく・大きく", "大きく": "おおきく・大きく",
    "おおはばに": "おおはばに・大幅に", "大幅に": "おおはばに・大幅に",
    "おおむね": "おおむね・概ね", "概ね": "おおむね・概ね",
    "おもいのほか": "おもいのほか・思いのほか", "思いのほか": "おもいのほか・思いのほか",
    "おもに": "おもに・主に", "主に": "おもに・主に",
    "かんぜんに": "かんぜんに・完全に", "完全に": "かんぜんに・完全に",
    "きょくりょく": "きょくりょく・極力", "極力": "きょくりょく・極力",
    "きわめて": "きわめて・極めて", "極めて": "きわめて・極めて",
    "けたちがいに": "けたちがいに・桁違いに", "桁違いに": "けたちがいに・桁違いに",
    "けっこう": "けっこう・結構", "結構": "けっこう・結構",
    "げんに": "げんに・厳に", "厳に": "げんに・厳に",
    "これいじょう": "これいじょう・これ以上", "これ以上": "これいじょう・これ以上",
    "さらに": "さらに・更に", "更に": "さらに・更に",
    "しょうしょう": "しょうしょう・少々", "少々": "しょうしょう・少々",
    "じゃっかん": "じゃっかん・若干", "若干": "じゃっかん・若干",
    "じゅうぶん": "じゅうぶん・十分", "十分": "じゅうぶん・十分",
    "すくなくとも": "すくなくとも・少なくとも", "少なくとも": "すくなくとも・少なくとも",
    "すこし": "すこし・少し", "少し": "すこし・少し",
    "すこぶる": "すこぶる・頗る", "頗る": "すこぶる・頗る",
    "すごく": "すごく・凄く", "凄く": "すごく・凄く",
    "すべて": "すべて・全て", "全て": "すべて・全て",
    "ずいぶん": "ずいぶん・随分", "随分": "ずいぶん・随分",
    "ぜったいに": "ぜったいに・絶対に", "絶対に": "ぜったいに・絶対に",
    "ぜんぜん": "ぜんぜん・全然", "全然": "ぜんぜん・全然",
    "そうとう": "そうとう・相当", "相当": "そうとう・相当",
    "たいして": "たいして・大して", "大して": "たいして・大して",
    "たいそう": "たいそう・大層", "大層": "たいそう・大層",
    "たいへん": "たいへん・大変", "大変": "たいへん・大変",
    "たくさん": "たくさん・沢山", "沢山": "たくさん・沢山",
    "たしょう": "たしょう・多少", "多少": "たしょう・多少",
    "ちょう": "超・ちょう・ちょー", "超": "超・ちょう・ちょー", "ちょー": "超・ちょう・ちょー",
    "つよく": "つよく・強く", "強く": "つよく・強く",
    "できるだけ": "できるだけ・出来るだけ", "出来るだけ": "できるだけ・出来るだけ",
    "とくに": "とくに・特に", "特に": "とくに・特に",
    "とびきり": "とびきり・飛び切り", "飛び切り": "とびきり・飛び切り",
    "なかなか": "なかなか・中々", "中々": "なかなか・中々",
    "なにも": "なにも・何も", "何も": "なにも・何も",
    "はげしく": "はげしく・激しく", "激しく": "はげしく・激しく",
    "はなはだ": "はなはだ・甚だ", "甚だ": "はなはだ・甚だ",
    "ばつぐんに": "ばつぐんに・抜群に", "抜群に": "ばつぐんに・抜群に",
    "ひじょうに": "ひじょうに・非常に", "非常に": "ひじょうに・非常に",
    "ひどく": "ひどく・酷く", "酷く": "ひどく・酷く",
    "ひろく": "ひろく・広く", "広く": "ひろく・広く",
    "ふかく": "ふかく・深く", "深く": "ふかく・深く",
    "ほとんど": "ほとんど・殆ど", "殆ど": "ほとんど・殆ど",
    "ほんとに": "ほんとに・本当に", "本当に": "ほんとに・本当に",
    "まことに": "まことに・誠に", "誠に": "まことに・誠に",
    "まじ": "まじ・マジ", "マジ": "まじ・マジ",
    "ますます": "ますます・益々", "益々": "ますます・益々",
    "まったく": "まったく・全く", "全く": "まったく・全く",
    "むちゃくちゃ": "むちゃくちゃ・無茶苦茶", "無茶苦茶": "むちゃくちゃ・無茶苦茶",
    "めちゃくちゃ": "めちゃくちゃ・滅茶苦茶", "滅茶苦茶": "めちゃくちゃ・滅茶苦茶",
    "もうすこし": "もうすこし・もう少し", "もう少し": "もうすこし・もう少し",
    "もっとも": "もっとも・最も", "最も": "もっとも・最も",
    "ものすごく": "ものすごく・物凄く", "物凄く": "ものすごく・物凄く",
    "よく": "よく・良く", "良く": "よく・良く",
    "よほど": "よほど・余程", "余程": "よほど・余程",
    "わりと": "わりと・割と", "割と": "わりと・割と",
    "めっちゃ": "めっちゃ・めちゃ", "メッチャ": "めっちゃ・めちゃ",

    "かなり": "かなり", "ごく": "ごく", "しっかり": "しっかり", "そこそこ": "そこそこ",
    "そこまで": "そこまで", "それなり": "それなり", "それほど": "それほど", "そんなに": "そんなに",
    "たっぷり": "たっぷり", "ちょっと": "ちょっと", "ちょっとした": "ちょっとした",
    "ちょっぴり": "ちょっぴり", "とっても": "とっても", "とても": "とても",
    "とんでもなく": "とんでもなく", "どうしても": "どうしても", "どうも": "どうも",
    "なるべく": "なるべく", "べらぼうに": "べらぼうに", "ほぼ": "ほぼ", "ほんの": "ほんの",
    "まあまあ": "まあまあ", "まだまだ": "まだまだ",
    "もっと": "もっと", "やたら": "やたら", "やや": "やや", "よっぽど": "よっぽど", "より": "より",
}

EN_ALL_MODIFIER_WORDS = [
    (r'\b' + re.escape(word) + r'\b', word)
    for word in {
        "a bit", "a hair", "a little", "a little bit", "a smidge", "a smidgen", "a tad",
        "a touch", "a whisker", "absolutely", "achingly", "adequately", "all but", "almost",
        "appreciably", "astonishingly", "astoundingly", "at all", "awfully", "barely",
        "basically", "blindingly", "bloody", "breathtakingly", "closely", "comparatively",
        "completely", "considerably", "crazily", "crazy", "damn", "dead", "deathly",
        "directly", "downright", "effing", "enormously", "enough", "entirely", "especially",
        "essentially", "exceptionally", "excessively", "exclusively", "extraordinarily",
        "extremely", "faintly", "freaking", "fricking", "frightfully", "fully",
        "fundamentally", "further", "genuinely", "goddamn", "greatly", "hardly", "hella",
        "highly", "hugely", "immensely", "in any way", "in detail", "in full", "incredibly",
        "indefinitely", "infinitely", "insanely", "intensely", "jolly", "just", "just about",
        "kind of", "kinda", "less than", "lil'", "literally", "mad", "marginally",
        "measurably", "mega", "merely", "mildly", "minimally", "moderately", "monumentally",
        "more", "most", "much", "nearly", "nominally", "notably", "noticeably", "only",
        "overly", "painfully", "perfectly", "phenomenally", "plain", "poorly", "positively",
        "practically", "profoundly", "proper", "proportionally", "quantifiably", "quite",
        "rather", "real", "really", "reasonably", "relatively", "remarkably", "ridiculously",
        "scarcely", "seriously", "sick", "significantly", "simply", "slightly", "so",
        "somewhat", "sort of", "sorta", "spectacularly", "staggeringly", "strictly",
        "strongly", "stunningly", "stupid", "stupidly", "substantially", "sufficiently",
        "supremely", "terribly", "the most", "thoroughly", "too", "totally", "tremendously",
        "truly", "ultra", "unbelievably", "unduly", "unsalvageably", "unusually", "utterly",
        "vaguely", "vastly", "very", "virtually", "way", "way too", "well", "wholly", "wicked",
    }
]
