# Import neophodnih biblioteka
from sklearn.linear_model import LinearRegression  # Model za linearnu regresiju
from sklearn.metrics import mean_squared_error  # Metrika za ocenjivanje modela (RMSE)
from sklearn.model_selection import train_test_split  # Za podelu podataka na train/test (da izbegnemo overfitting)
import pandas as pd  # Za učitavanje i manipulaciju podataka
import numpy as np  # Za rad sa nizovima i matematičke operacije
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Učitaj podatke iz CSV fajla (promeni putanju ako treba)
df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "merged_trends_influenza_wide.csv")

# Odaberi prediktore (X): top 3 ključne reči, sa lagom -2 nedelje (pretrage prethode slučajevima za 2 nedelje)
# shift(2) pomera kolone za 2 reda dole (lag -2); promeni na shift(8) za lag -8 ako želiš testirati duži lag
X = df[["grip", "virus gripa", "simptomi gripa"]].shift(1)

# Ciljna promenljiva (y): broj slučajeva influence
y = df["INF_ALL"]

# Ukloni redove sa nedostajućim vrednostima (NaN) u X ili y
mask = ~X.isna().any(axis=1) & ~y.isna()
X = X[mask]
y = y[mask]

# Podeli podatke na train (80%) i test (20%) set - ovo je važno da proverimo da li model radi na neviđenim podacima
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)  # random_state za reproducibilnost

# Kreiraj i treniraj model na train setu
model = LinearRegression()
model.fit(X_train, y_train)

# Predvidi na train setu (da vidimo kako se uklapa na poznatim podacima)
y_train_pred = model.predict(X_train)

# Predvidi na test setu (da vidimo performanse na neviđenim podacima)
y_test_pred = model.predict(X_test)

# Izračunaj metrike za train set
r2_train = model.score(X_train, y_train)
rmse_train = np.sqrt(mean_squared_error(y_train, y_train_pred))

# Izračunaj metrike za test set
r2_test = model.score(X_test, y_test)
rmse_test = np.sqrt(mean_squared_error(y_test, y_test_pred))

# Ispiši rezultate
print(f"Train R^2: {r2_train:.3f}")
print(f"Train RMSE: {rmse_train:.3f}")
print(f"Test R^2: {r2_test:.3f}")
print(f"Test RMSE: {rmse_test:.3f}")

# Koeficijenti modela (koliko svaka reč utiče na predikciju)
print("\nKoeficijenti modela:")
for feature, coef in zip(X.columns, model.coef_):
    print(f"{feature}: {coef:.3f}")

print(f"Intercept: {model.intercept_:.3f}")
