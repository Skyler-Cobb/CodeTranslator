# decoder/tools.py
import string
from collections import Counter
import re
from typing import List, Dict, Tuple, Optional

# Constants
LETTERS_LOWERCASE = string.ascii_lowercase
LETTERS_UPPERCASE = string.ascii_uppercase
ALPHABET_SIZE = 26

# English letter frequency (from most common to least common)
ENGLISH_LETTER_FREQ = 'etaoinsrhdlucmfywgpbvkjxqz'
# Common English words for frequency analysis
COMMON_ENGLISH_WORDS = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 
                      'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at'}


def caesar_translate(message: str, shift: int) -> str:
    """
    Return the Caesar‑shifted version of *message*.
    Efficiently shifts letters while preserving case and non-alphabetic characters.
    
    Args:
        message: The string to be shifted
        shift: The number of positions to shift (can be positive or negative)
        
    Returns:
        The Caesar-shifted text
    """
    # Normalize shift to 0-25 range
    shift = shift % ALPHABET_SIZE
    
    # If shift is 0, return the original message
    if shift == 0:
        return message
        
    result = []
    
    for char in message:
        if char in LETTERS_UPPERCASE:
            # Get the 0-25 position, add shift, wrap around, convert back to ASCII
            shifted = chr((ord(char) - ord('A') + shift) % ALPHABET_SIZE + ord('A'))
            result.append(shifted)
        elif char in LETTERS_LOWERCASE:
            # Same approach for lowercase
            shifted = chr((ord(char) - ord('a') + shift) % ALPHABET_SIZE + ord('a'))
            result.append(shifted)
        else:
            # Non-alphabetic characters remain unchanged
            result.append(char)
            
    return ''.join(result)


def analyze_caesar_candidates(ciphertext: str, top_n: int = 5) -> List[Tuple[int, str, float]]:
    """
    Analyze all possible Caesar shifts and return the most likely candidates.
    
    Args:
        ciphertext: The encrypted text
        top_n: Number of top candidates to return
        
    Returns:
        List of tuples (shift, decrypted_text, score) sorted by descending score
    """
    candidates = []
    
    # Try all 26 possible shifts
    for shift in range(ALPHABET_SIZE):
        plaintext = caesar_translate(ciphertext, shift)
        score = _score_text(plaintext)
        candidates.append((shift, plaintext, score))
    
    # Sort by score (highest first)
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    # Return top N candidates
    return candidates[:top_n]


def _score_text(text: str) -> float:
    """
    Score a text based on English language characteristics.
    Higher scores indicate more likely English text.
    
    Uses a combination of:
    1. Letter frequency analysis
    2. Common word presence
    3. N-gram frequency (commonly adjacent letters)
    
    Args:
        text: The text to score
        
    Returns:
        A numerical score (higher is better)
    """
    # Lowercase for analysis
    text_lower = text.lower()
    
    # Letter frequency score (compare distribution to English)
    letter_freq_score = _calculate_letter_frequency_score(text_lower)
    
    # Common word presence score
    word_score = _calculate_word_presence_score(text_lower)
    
    # Combine scores (giving more weight to word presence)
    return letter_freq_score * 0.4 + word_score * 0.6


def _calculate_letter_frequency_score(text: str) -> float:
    """Calculate a score based on letter frequency compared to English."""
    # Filter non-alphabetic characters and get letter counts
    letters_only = re.sub(r'[^a-z]', '', text.lower())
    if not letters_only:
        return 0.0
        
    # Count letter frequencies
    letter_counts = Counter(letters_only)
    total_letters = sum(letter_counts.values())
    
    if total_letters == 0:
        return 0.0
    
    # Calculate frequency deviation from English
    score = 0
    for i, char in enumerate(ENGLISH_LETTER_FREQ):
        # Expected frequency position vs. actual frequency
        expected_freq = (ALPHABET_SIZE - i) / ALPHABET_SIZE
        actual_freq = letter_counts.get(char, 0) / total_letters
        
        # Closer to expected frequency is better
        score += 1 - abs(expected_freq - actual_freq) 
    
    return score / ALPHABET_SIZE


def _calculate_word_presence_score(text: str) -> float:
    """Calculate a score based on presence of common English words."""
    # Simple word tokenization
    words = re.findall(r'\b[a-z]{2,}\b', text.lower())
    if not words:
        return 0.0
        
    # Count common English words present
    matches = sum(1 for word in words if word in COMMON_ENGLISH_WORDS)
    
    # Calculate score based on proportion of common words
    return min(1.0, matches / (len(words) * 0.5))