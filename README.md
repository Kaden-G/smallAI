### `README.md`

````markdown
# SmallAI: Natural Language to Splunk Query

This project converts **natural language (NL) log queries** into valid **Splunk SPL** using a hybrid approach:

- **ML-first**: TF-IDF + Logistic Regression slot classifiers predict `action`, `time`, `user`, and `source`.
- **Rule fallback**: If ML confidence is low, rule-based regex fills the gap.
- **Normalization**: Handles variations like `yesterday → last24h`.
- **Clarification prompts**: If key fields are missing, the CLI interactively asks for them.
- **Force mode**: Run with `-f` to skip prompts and auto-fill with wildcards.

The result is a system that’s both **flexible (ML)** and **reliable (rules + clarification)**, producing realistic Splunk SPL queries.

---

## Why This Matters

Splunk is powerful, but writing SPL queries is often a barrier.  
This project makes log search **as simple as asking in plain English**:

```text
show me failed logins from yesterday
````

Becomes:

```spl
index=auth sourcetype=sshd ("Failed password" OR "auth failure") earliest=-24h@h latest=now
```

---

## Features

* ✅ ML-first parsing with per-slot confidence
* ✅ Rule-based fallback for edge cases
* ✅ Interactive clarification for missing fields (source, user)
* ✅ Force mode (`-f`) to skip prompts for automation
* ✅ Realistic SPL query generation with `sourcetype`, `index`, and common search terms

---

## Installation

```bash
git clone https://github.com/<your-username>/smallAI.git
cd smallAI
pip install -r requirements.txt
```

### Dependencies

* Python 3.9+
* scikit-learn
* numpy

---

## Usage

### Interactive Mode (default)

```bash
./hybrid_parser.py "show me failed logins from yesterday"
```

If the query is missing details, you’ll be asked:

```
Missing field: source
[1] auth
[2] ssh
[3] web
[4] database
[5] filesystem
[6] host
[0] I don't know (keep *)

Choose a source: 1
```

### Force Mode (skip prompts)

```bash
./hybrid_parser.py -f "show me failed logins from yesterday"
```

Output:

```
⚡ Running in force mode: skipping clarification prompts.

NL Query: show me failed logins from yesterday
Hybrid Parsed: {'action': 'failure', 'time': 'last24h', 'user': '*', 'source': '*'}
Generated SPL: index=* sourcetype=sshd ("Failed password" OR "auth failure") earliest=-24h@h latest=now
```

---

## Repo Structure

```
smallAI/
│
├── dataset/
│   └── log_query_dataset.csv   # synthetic training/eval queries
│
├── rule_based_parser.py        # regex-based baseline parser
├── hybrid_parser.py            # ML + rules + SPL generator
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Results

* **Rule-based baseline:** \~90% slot accuracy, brittle on phrasing
* **ML parser:** \~95% slot accuracy, especially strong on time expressions
* **Hybrid parser:** best of both worlds, reliable with fallback and prompts

---

## Future Work

* Expand Splunk `action_map` with more sourcetypes and fields
* Add a **Streamlit web demo** (drop-downs instead of CLI prompts)
* Integrate with a **real Splunk instance** for live query validation
* Explore **NER models (spaCy, DistilBERT)** for better generalization

---

## License

MIT

```

