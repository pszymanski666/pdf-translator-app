**1. Wprowadzenie i Cel**

Celem projektu jest stworzenie prostej aplikacji demonstracyjnej w Streamlit, która umożliwia tłumaczenie treści z plików PDF nieposiadających warstwy tekstowej. Aplikacja wykorzysta Tesseract OCR do ekstrakcji tekstu z obrazów stron PDF, a następnie użyje modelu LLM (google/gemma-3-27b-it) za pośrednictwem API OpenRouter do przetłumaczenia tekstu na wybrany język. Aplikacja ma na celu pokazanie integracji tych technologii w prostym przepływie pracy. **Klucz API do OpenRouter będzie zdefiniowany bezpośrednio w kodzie źródłowym na potrzeby tej demonstracji.**

**2. Kluczowe Funkcjonalności**

*   **F1: Upload Pliku PDF:**
    *   Użytkownik może załadować plik w formacie PDF za pomocą komponentu `st.file_uploader`.
    *   Aplikacja powinna akceptować tylko pliki z rozszerzeniem `.pdf`.
    *   Zakładamy, że PDF zawiera obrazy stron (brak warstwy tekstowej).
*   **F2: Wybór Języka OCR:**
    *   Użytkownik może wybrać język źródłowy (dla Tesseract OCR) z predefiniowanej listy: Angielski (eng), Niemiecki (deu), Polski (pol), Gruziński (kat), Ukraiński (ukr).
    *   Użyj komponentu `st.selectbox` lub `st.radio`.
*   **F3: Wybór Języka Tłumaczenia:**
    *   Użytkownik może wybrać język docelowy (dla tłumaczenia LLM) z tej samej listy co w F2: Angielski, Niemiecki, Polski, Gruziński, Ukraiński.
    *   Użyj komponentu `st.selectbox` lub `st.radio`.
*   **F4: Przycisk Uruchamiający Proces:** *(Poprzednio F5)*
    *   Przycisk (`st.button`), np. "Przetłumacz", który inicjuje cały proces po załadowaniu pliku i wybraniu języków.
*   **F5: Ekstrakcja Obrazów z PDF:** *(Poprzednio F6)*
    *   Po kliknięciu przycisku, aplikacja przetwarza załadowany plik PDF za pomocą biblioteki **`PyMuPDF` (fitz)**.
    *   Dla **każdej strony** PDF generuje obraz w formacie PNG o wystarczającej rozdzielczości dla OCR (np. 300 DPI).
*   **F6: OCR za pomocą Tesseract:** *(Poprzednio F7)*
    *   Wykorzystaj Tesseract OCR do przetworzenia wygenerowanych obrazów PNG (z F5), strona po stronie.
    *   Użyj języka wybranego przez użytkownika w F2.
    *   **Połącz tekst odzyskany ze wszystkich stron** w jedną, ciągłą zmienną tekstową.
*   **F7: Tłumaczenie Tekstu przez OpenRouter API:** *(Poprzednio F8)*
    *   Przygotuj prompt dla modelu `google/gemma-3-27b-it` zawierający:
        *   Opcjonalny, predefiniowany w kodzie `system_message` (pozostaw miejsce na jego edycję w kodzie).
        *   Polecenie tłumaczenia **całego połączonego tekstu** uzyskanego z OCR (F6) na język docelowy wybrany w F3. Np.: "Translate the following text from [Język OCR] to [Język Tłumaczenia]:\n\n[Połączony tekst z OCR]"
    *   Wyślij zapytanie do API OpenRouter (`https://openrouter.ai/api/v1/chat/completions`) używając **klucza API zdefiniowanego jako stała w kodzie aplikacji**.
    *   Skonfiguruj żądanie, aby otrzymywać odpowiedź w trybie **streamingu tokenów**.
*   **F8: Wyświetlanie Przetłumaczonego Tekstu:** *(Poprzednio F9)*
    *   Wyświetl przetłumaczony tekst użytkownikowi w czasie rzeczywistym, w miarę otrzymywania kolejnych tokenów z API.
    *   Użyj komponentu `st.write` lub `st.markdown` z funkcją `st.write_stream`.

**3. Stos Technologiczny**

*   **Język:** Python 3.9+
*   **Interfejs Użytkownika:** Streamlit
*   **OCR:** Tesseract OCR (poprzez wrapper `pytesseract`)
*   **Ekstrakcja obrazów z PDF:** **`PyMuPDF` (fitz)**
*   **API LLM:** OpenRouter API
*   **Model LLM:** `google/gemma-3-27b-it`
*   **Biblioteka do komunikacji HTTP:** `requests` lub `httpx` (preferowane `httpx` dla async, chociaż dla streamingu `requests` też wystarczy)

**4. Interfejs Użytkownika (Streamlit Layout)**

Prosty, jednoekranowy interfejs:

1.  Tytuł aplikacji (np. "PDF Translator Demo").
2.  Komponent `st.file_uploader` do ładowania PDF.
3.  Dwa `st.selectbox`: jeden dla języka OCR, drugi dla języka tłumaczenia.
4.  Przycisk `st.button` "Przetłumacz".
5.  Miejsce na wyświetlenie wyniku (`st.write` / `st.markdown` / `st.text_area`), które będzie aktualizowane strumieniowo.
6.  *Opcjonalnie:* Można dodać `st.expander` pokazujący tekst po OCR przed tłumaczeniem dla celów diagnostycznych.

**5. Szczegóły Implementacji**

*   **Klucz API OpenRouter:** Zdefiniuj klucz API jako stałą (zmienna globalna) w kodzie aplikacji, np. `OPENROUTER_API_KEY = "sk-or-v1-..."`. **Pamiętaj, aby nie umieszczać prawdziwego klucza w publicznych repozytoriach.** W kodzie można dodać komentarz wyjaśniający, gdzie użytkownik powinien wstawić swój klucz.
*   **System Message:** W kodzie zdefiniuj zmienną `SYSTEM_MESSAGE` (np. pusty string lub proste polecenie typu "You are a helpful translation assistant."), którą można łatwo zmodyfikować. Przekaż ją w strukturze `messages` do API OpenRouter.
*   **Streaming:** Użyj parametru `stream=True` w zapytaniu do OpenRouter API i iteruj po odpowiedzi, aby odbierać tokeny. Aktualizuj dynamicznie komponent Streamlit (`st.write_stream`).
*   **Obsługa Błędów:** Minimalna. Wystarczy podstawowy `try...except` wokół wywołań API i przetwarzania plików, informujący użytkownika o problemie za pomocą `st.error()`. Nie implementuj szczegółowej logiki ponowień czy walidacji.
*   **Zależności:** Przygotuj plik `requirements.txt` z potrzebnymi bibliotekami (`streamlit`, `pytesseract`, `PyMuPDF`, `requests` lub `httpx`, `openai` - klient OpenRouter jest kompatybilny z OpenAI SDK).

**6. Poza Zakresem (Out of Scope)**

*   Bezpieczne zarządzanie kluczem API (poza hardkodowaniem).
*   Uwierzytelnianie i autoryzacja użytkowników.
*   Zaawansowana obróbka wstępna obrazów przed OCR (denoising, deskewing).
*   Szczegółowe logowanie zdarzeń.
*   Rozbudowana obsługa błędów i przypadków brzegowych (np. PDF zabezpieczone hasłem, PDF bez obrazów, błędy sieciowe z OpenRouter inne niż podstawowe, nieprawidłowy klucz API).
*   Zapisywanie historii tłumaczeń.
*   Optymalizacja wydajności dla bardzo dużych plików PDF.
*   Interfejs użytkownika wykraczający poza podstawowe komponenty Streamlit.
*   Automatyczne wykrywanie języka źródłowego.