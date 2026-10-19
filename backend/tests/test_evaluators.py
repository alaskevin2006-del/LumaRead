import pytest
from app.evaluators import normalize,word_tokens

def test_tokens_preserve_repeated_words_and_punctuation():
    text='The dog sees the dog. It\'s red!'
    words=word_tokens(text)
    assert [w['text'] for w in words]==['The','dog','sees','the','dog',"It's",'red']
    assert all(text[w['char_start']:w['char_end']]==w['text'] for w in words)

def test_missing_scores_not_fabricated():
    with pytest.raises(ValueError):normalize({'score':90,'differences':{'errors':[]}},'The dog.','openpronounce')
    result=normalize({'overall_score':60,'words':[{'score':90},{'score':None}]},'The dog.','remote')
    assert result['words'][1]['level']=='unknown'
    assert result['accuracy'] is None

def test_score_bounds():
    with pytest.raises(ValueError):normalize({'overall_score':101,'words':[{'score':90}]},'Hello','remote')
