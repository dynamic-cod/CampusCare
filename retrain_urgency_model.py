"""
retrain_urgency_model.py
Retrains the CampusCare urgency TF-IDF + LogisticRegression model,
adding 25+ URGENT life-safety examples (snakes, beehives, fire, structural hazards).

Run from project root with the venv active:
    python retrain_urgency_model.py
"""
import json
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Bootstrap Django so we can optionally inspect the DB (not strictly needed)
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")

import django
django.setup()

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# ============================================================
# TRAINING DATA
# ============================================================

TRAINING_DATA = [
    # ─── URGENT – Life-Safety / EMERG ───────────────────────
    ("snake found in room 203 sir syed hall boys hostel please help urgent", "urgent"),
    ("live cobra spotted near hostel gate aftab hall please send help immediately", "urgent"),
    ("something slithering under my bed in my hostel room terrified please send rescue team", "urgent"),
    ("saamp dekha hai kamre mein hostel block B please koi aaye abhi", "urgent"),
    ("viper sighting near wash area Abdullah hall girls hostel urgent rescue needed", "urgent"),
    ("python spotted coiled in bathroom hostel room 112 students evacuating", "urgent"),
    ("reptile spotted in corridor Hadi Hasan Hall Floor 2 students scared", "urgent"),
    ("scorpion found inside hostel wardrobe stung student medical attention needed", "urgent"),
    ("large beehive near balcony of room 305 students cannot open windows hornet nest", "urgent"),
    ("wasp nest on window grill hostel block 4 students getting stung daily", "urgent"),
    ("massive bee swarm near hostel entrance blocking main door emergency response needed", "urgent"),
    ("hornet colony under AC unit hostel room students afraid to stay", "urgent"),
    ("smoke smell coming from electrical room hostel ground floor possible fire", "urgent"),
    ("cylinder leak in mess kitchen gas smell strong evacuation started", "urgent"),
    ("fire in hostel room mattress caught fire students evacuating floor 3", "urgent"),
    ("gas leak from broken pipe canteen building strong smell emergency", "urgent"),
    ("smoke filling corridor from room 108 Ross Masood Hall fire suspected", "urgent"),
    ("dog bite incident near hostel gate student injured needs medical help immediately", "urgent"),
    ("rabid dog inside campus attacking students proctorial squad needed urgently", "urgent"),
    ("monkey attack on student near library snatched belongings injured", "urgent"),
    ("aggressive monkey colony entering hostel rooms biting students SOS", "urgent"),
    ("ceiling collapsed in hostel room 214 student injured structural emergency", "urgent"),
    ("wall crack in hostel building structural damage residents evacuated", "urgent"),
    ("electrocution risk exposed live wire in hostel corridor extremely dangerous", "urgent"),
    ("live electrical wire touching water puddle corridor hostel ground floor urgent", "urgent"),
    ("mysterious creature crawling in hostel washroom looks like a serpent panicking", "urgent"),
    ("strange animal with scales spotted in hostel common room please investigate", "urgent"),
    ("burning smell from mess gas line potential cylinder explosion risk", "urgent"),
    ("there is a snake in my hostel please somebody come now URGENT", "urgent"),
    ("kuch ripta hua jaisa dikh raha hai kamre mein shayad saamp ho immediate help", "urgent"),

    # ─── HIGH – Serious maintenance but not life-safety ─────
    ("water pipe burst flooding hostel corridor immediate repair needed", "high"),
    ("electricity gone in entire hostel block since 6 hours exam tomorrow", "high"),
    ("sewage overflow in washroom ground floor foul smell health hazard", "high"),
    ("fan fell from ceiling in classroom narrowly missed student", "high"),
    ("lift not working since two days students on floor 5 struggling", "high"),
    ("water supply completely cut off girls hostel for 12 hours", "high"),
    ("short circuit in room causing sparks electrician required urgently", "high"),
    ("fire alarm malfunction going off continuously disturbing residents", "high"),
    ("window glass broken hostel room security risk open space", "high"),
    ("AC unit leaking water causing floor damage and slipping hazard", "high"),
    ("CCTV cameras not working near hostel entrance security concern", "high"),
    ("major plumbing leak under mess kitchen floor needs urgent repair", "high"),
    ("geyser sparking when switched on could cause electrocution", "high"),
    ("door lock broken cannot lock room from inside security issue", "high"),

    # ─── NORMAL – Standard maintenance ──────────────────────
    ("fan making noise in hostel room please fix", "normal"),
    ("tube light flickering in room 304 needs replacement", "normal"),
    ("WiFi connectivity issue in Abdullah Hall slow internet", "normal"),
    ("mess food quality poor this week please improve", "normal"),
    ("room door hinge broken needs repair carpenter required", "normal"),
    ("window latch broken in my hostel room", "normal"),
    ("drinking water cooler not working in hostel common area", "normal"),
    ("projector not working in lecture hall B102", "normal"),
    ("library printer is out of paper and toner", "normal"),
    ("mess timings changed without notice students inconvenienced", "normal"),
    ("sofa in common room torn needs replacement", "normal"),
    ("toilet flush not working properly in hostel washroom", "normal"),
    ("corridor light not working floor 2 dark at night", "normal"),
    ("dining hall chairs broken need replacement", "normal"),
    ("sports ground grass overgrown maintenance needed", "normal"),
    ("notice board in department broken", "normal"),
    ("phone charging point in common area not working", "normal"),
    ("leaking tap in hostel washroom needs repair", "normal"),
    ("room heater not functioning in winter", "normal"),
    ("mess utensils need proper cleaning", "normal"),
    ("internet portal login issue student unable to access", "normal"),
    ("classroom dustbin overflowing needs cleaning", "normal"),
    ("bicycle stand near library damaged", "normal"),
    ("dispenser in hostel corridor empty needs refilling", "normal"),
    ("AC filter dirty needs cleaning in faculty room", "normal"),
    ("computer lab printer jam needs technician", "normal"),
    ("mess water cooler has odd smell", "normal"),
    ("campus road pothole near engineering college gate", "normal"),
    ("broken bench outside hostel common room", "normal"),

    # ─── LOW – Minor cosmetic / administrative ───────────────
    ("paint peeling on hostel room wall cosmetic issue", "low"),
    ("request for extra bed in hostel room", "low"),
    ("missing nameplate on hostel room door", "low"),
    ("grass near hostel needs trimming", "low"),
    ("request for additional dustbin near hostel common area", "low"),
    ("mess notice board needs updating with new menu", "low"),
    ("suggest adding more seating in common room", "low"),
    ("request for mirror in hostel washroom", "low"),
    ("footpath near science faculty needs minor repair", "low"),
    ("request for more lighting in garden area", "low"),
    ("complaint about noise from construction near hostel", "low"),
    ("request for water dispenser in library reading room", "low"),
    ("broken clock in corridor", "low"),
    ("request for shoe rack near hostel entrance", "low"),
    ("library book missing from shelf complaint", "low"),
    ("minor wall crack cosmetic no structural issue", "low"),
    ("missing towel hook in washroom", "low"),
    ("garden area maintenance needed trimming hedges", "low"),
    ("request for umbrella stand near hostel gate", "low"),
    ("mess suggestion box broken need replacement", "low"),
    ("corridor matting worn out needs replacement", "low"),
    ("parking area needs white line repainting", "low"),
    ("sports equipment request cricket bat missing", "low"),
    ("minor leakage from terrace cosmetic water stain only", "low"),
    ("request for insect repellent spray in hostel monthly routine", "low"),
    ("wooden cabinet door slightly misaligned minor issue", "low"),
]

# ============================================================
# TRAIN
# ============================================================

def train():
    texts, labels = zip(*TRAINING_DATA)

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=8000,
            sublinear_tf=True,
            strip_accents="unicode",
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
            min_df=1,
        )),
        ("classifier", LogisticRegression(
            C=5.0,
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
            multi_class="multinomial",
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {acc:.4f} ({len(X_test)} samples)")

    # Verify snake / safety keywords are classified URGENT
    test_cases = [
        "snake found in hostel room",
        "saamp dekha hai kamre mein",
        "beehive near balcony urgent",
        "gas leak cylinder mess kitchen",
        "something slithering under bed",
        "rabid dog attacking students campus",
        "ceiling collapsed hostel room",
        "live wire touching water corridor",
    ]
    print("\n── Safety keyword inference check ──")
    for tc in test_cases:
        pred = pipeline.predict([tc])[0]
        proba = dict(zip(pipeline.classes_, pipeline.predict_proba([tc])[0]))
        print(f"  [{pred.upper():7s}] {tc[:60]}")
        if pred != "urgent":
            print(f"    ⚠ WARNING: Expected URGENT, got {pred}. Probas: {proba}")

    # Save model
    model_path = os.path.join("core", "ml_models", "urgency_classifier.joblib")
    joblib.dump(pipeline, model_path)
    print(f"\n✓ Model saved → {model_path}")

    metadata = {
        "model_name": "TFIDF_LogisticRegression_Urgency_Classifier_v2_Emergency",
        "features": ["combined_text"],
        "trained_at": datetime.utcnow().isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "test_accuracy": round(acc, 6),
        "classes": sorted(set(labels)),
        "safety_guardrail": "enabled",
    }
    meta_path = os.path.join("core", "ml_models", "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved → {meta_path}")
    return pipeline


if __name__ == "__main__":
    print("=" * 60)
    print("CampusCare Urgency Model Retrainer v2 (Emergency-Aware)")
    print("=" * 60)
    train()
    print("\nDone.")
