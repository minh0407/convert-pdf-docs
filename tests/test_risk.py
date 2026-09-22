from app.analyzers.risk import region_risks, classify_page

def test_special_symbol_detection():
    flags = region_risks('220V ± 10%', 0.95)
    assert 'SPECIAL_SYMBOL' in flags

def test_low_confidence_detection():
    flags = region_risks('abc', 0.55)
    assert 'LOW_CONFIDENCE' in flags

def test_page_easy():
    regions = [
        {'text': 'Xin', 'confidence': 0.96},
        {'text': 'chào', 'confidence': 0.94},
    ]
    result = classify_page(regions, {'blur_score': 200, 'dark_ratio': 0.01})
    assert result['difficulty'] == 'easy'
