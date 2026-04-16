import pickle

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

DATA_PATH = "students.csv"
MODEL_PATH = "model.pkl"

# Load dataset from CSV
students = pd.read_csv(DATA_PATH)
expected_columns = {"marks", "stream", "interest", "skill", "talent", "education", "career"}
if not expected_columns.issubset(students.columns):
    missing = expected_columns - set(students.columns)
    raise ValueError(f"Missing required columns in {DATA_PATH}: {missing}")

# Preprocessing: encode categorical variables using one-hot encoding
features = students[["marks", "stream", "interest", "skill", "talent", "education"]]
X = pd.get_dummies(features, columns=["stream", "interest", "skill", "talent", "education"])
y = students["career"]

# Split dataset into features and target
min_class_count = y.value_counts().min()
stratify_target = y if min_class_count >= 2 else None
if stratify_target is None:
    print("Warning: some career labels have fewer than 2 examples; using a non-stratified train/test split.")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=stratify_target
)

# Train a random forest classifier
classifier = RandomForestClassifier(n_estimators=100, random_state=42)
classifier.fit(X_train, y_train)

# Evaluate model accuracy
y_pred = classifier.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Random Forest accuracy: {accuracy:.4f}")
print("Classification report:")
print(classification_report(y_test, y_pred))

# Train a clustering model to group similar students together
cluster_count = min(5, max(2, len(students) // 20))
clusterer = KMeans(n_clusters=cluster_count, random_state=42)
cluster_labels = clusterer.fit_predict(X)
students["cluster"] = cluster_labels
print("Cluster membership counts:")
print(students["cluster"].value_counts().sort_index())

# Save trained classifier and preprocessing columns
model_data = {
    "model": classifier,
    "columns": X.columns.tolist(),
    "clusterer": clusterer,
}
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model_data, f)

print(f"Saved trained model to {MODEL_PATH}")
