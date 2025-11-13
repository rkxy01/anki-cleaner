# Efficiency Improvements Report for anki-cleaner

## Overview
This report identifies several areas in the `anki.py` file where code efficiency can be improved. The improvements range from algorithmic optimizations to better Python practices.

## Identified Efficiency Issues

### 1. **Inefficient Individual Note Updates (High Impact)**
**Location:** `anki.py:41-45` (update_notes method)

**Issue:** The `update_notes` method updates notes one by one in a loop, making individual API calls for each note. This results in N API calls for N notes, which is extremely inefficient for large datasets.

```python
for note in notes:
    note_id = note['noteId']
    fields = {key: value['value'] for key, value in note['fields'].items()}
    self._post("updateNoteFields", {"note": {"id": note_id, "fields": fields}})
    print(f"Updated note: {note_id}")
```

**Impact:** High - For 100 notes, this makes 100 separate HTTP requests instead of potentially 1 batch request.

**Recommendation:** Check if AnkiConnect supports batch update operations (like `updateNotesFields`). If so, batch all updates into a single API call.

---

### 2. **Uncompiled Regular Expressions (Medium Impact)**
**Location:** `anki.py:61, 80-84, 92` (format_listening_html method)

**Issue:** Regular expressions are compiled on every function call rather than being pre-compiled as class or module-level constants.

```python
string = re.sub(r'<br>|</?div>|&nbsp;', '', string)  # Line 61
string = re.sub(r'([.!?])(?!\s)', r'\1 ', string)    # Lines 80-84
string = re.sub(r'\s{2,}', ' ', string)              # Line 92
```

**Impact:** Medium - Regex compilation overhead on every call. For processing many notes, this adds up.

**Recommendation:** Pre-compile regex patterns as class-level constants:
```python
CLEANUP_PATTERN = re.compile(r'<br>|</?div>|&nbsp;')
PUNCTUATION_PATTERN = re.compile(r'([.!?])(?!\s)')
WHITESPACE_PATTERN = re.compile(r'\s{2,}')
```

---

### 3. **Inefficient String Replacement in Loop (Medium Impact)**
**Location:** `anki.py:72-77, 88-89` (format_listening_html method)

**Issue:** Uses `string.replace()` in loops, which creates a new string object on each iteration. This is O(n*m) where n is the number of matches and m is the string length.

```python
for i, match in enumerate(matches):
    placeholder = f"{tag_base}{i}__"
    string = string.replace(match, placeholder)  # Creates new string each time
    protected[placeholder] = match
```

**Impact:** Medium - For strings with many matches, this creates many intermediate string objects.

**Recommendation:** Build a replacement mapping and use a single regex substitution, or use a more efficient approach with regex callbacks.

---

### 4. **Unnecessary Dictionary Comprehension (Low Impact)**
**Location:** `anki.py:43` (update_notes method)

**Issue:** Dictionary comprehension is created for every note, even though it's only used once immediately after.

```python
fields = {key: value['value'] for key, value in note['fields'].items()}
```

**Impact:** Low - Minor overhead, but could be inlined if the API call is restructured.

**Recommendation:** If batching updates (Issue #1), this can be optimized as part of that refactor.

---

### 5. **No Change Detection Before Update (Medium Impact)**
**Location:** `anki.py:107-116` (reform_listening function)

**Issue:** The code formats all notes and updates them, even if the formatted value is identical to the original. This results in unnecessary API calls and database writes.

```python
for note in notes:
    if not 'Text' in note['fields']:
        print("ignore:", note)
        continue
    text_field = note['fields']['Text']['value']
    note['fields']['Text']['value'] = formatter.format_listening_html(text_field)
```

**Impact:** Medium - Unnecessary updates for notes that don't need changes.

**Recommendation:** Only add notes to the update list if the formatted value differs from the original:
```python
formatted_text = formatter.format_listening_html(text_field)
if formatted_text != text_field:
    note['fields']['Text']['value'] = formatted_text
    notes_to_update.append(note)
```

---

### 6. **Non-Pythonic Membership Test (Low Impact)**
**Location:** `anki.py:108`

**Issue:** Uses `not 'Text' in note['fields']` instead of the more Pythonic `'Text' not in note['fields']`.

```python
if not 'Text' in note['fields']:
```

**Impact:** Low - Readability issue, no performance impact.

**Recommendation:** Use `'Text' not in note['fields']` for better readability.

---

### 7. **Redundant Formatter Instantiation (Low Impact)**
**Location:** `anki.py:101`

**Issue:** Creates a `Formatter()` instance even though all methods are static. This is unnecessary object creation.

```python
formatter = Formatter()
```

**Impact:** Low - Minimal overhead, but unnecessary.

**Recommendation:** Call static methods directly: `Formatter.format_listening_html(text_field)` or make Formatter a module with functions instead of a class.

---

### 8. **Missing Error Handling for Network Requests (Reliability)**
**Location:** `anki.py:11-16` (_post method)

**Issue:** No timeout specified for HTTP requests, and no handling of connection errors. This can cause the script to hang indefinitely.

```python
response = requests.post(f"http://localhost:{self.port}", json={...})
```

**Impact:** Reliability - Script can hang on network issues.

**Recommendation:** Add timeout and proper error handling:
```python
response = requests.post(f"http://localhost:{self.port}", 
                        json={...}, 
                        timeout=30)
```

---

## Priority Recommendations

### High Priority
1. **Batch note updates** (Issue #1) - Biggest performance impact
2. **Add change detection** (Issue #5) - Avoid unnecessary updates

### Medium Priority
3. **Pre-compile regex patterns** (Issue #2) - Consistent performance improvement
4. **Optimize string replacements** (Issue #3) - Better for large strings

### Low Priority
5. **Fix Pythonic style** (Issue #6) - Code quality
6. **Remove unnecessary instantiation** (Issue #7) - Minor cleanup
7. **Add timeout to requests** (Issue #8) - Reliability improvement

## Estimated Impact

For a deck with 1000 notes where 500 need updates:
- **Current:** ~1000+ API calls (get IDs + get info + 1000 updates)
- **With optimizations:** ~3 API calls (get IDs + get info + 1 batch update) + 50% fewer updates due to change detection
- **Performance improvement:** ~300x faster for the update phase

## Conclusion

The most impactful improvements are batching updates and detecting changes before updating. These two changes alone could reduce API calls by over 99% in typical usage scenarios.
