import json

def break_words(lyrics):
    res = []
    for word in lyrics.split():
        line = {"text": word, "start": 0, "end": 0}
        res.append(line)
    return res

if __name__ == "__main__":
    lyrics = "Ⲧⲟⲛ ⲥⲩⲛⲁⲛⲁⲣⲭⲟⲛ Ⲗⲟⲅⲟⲛ Ⲡⲁⲧⲣⲓ ⲕⲉ Ⲡ̀ⲛⲉⲩⲙⲁⲧⲓ: ⲧⲟⲛ ⲉⲕ ⲡⲁⲣⲑⲉⲛⲟⲩ ⲧⲉⲭⲑⲉⲛⲧⲁ ⲓⲥ ⲥⲱⲧⲏⲣⲓⲁⲛ ⲏ̀ⲙⲟⲛ: ⲁ̀ⲛⲩⲙⲛⲏⲥⲱⲙⲉⲛ ⲡⲓⲥⲧⲓ ⲕⲉ ⲡ̀ⲣⲟⲥⲕⲩⲛⲏⲥⲱⲙⲉⲛ: ⲟ̀ⲧⲓ ⲏⲩⲇⲟⲕⲏⲥⲉ ⲥⲁⲣⲕⲓ: ⲁ̀ⲛⲉⲗⲑⲓⲛ ⲉⲛ ⲧⲱ ⲥ̀ⲧⲁⲩⲣⲟ: ⲕⲉ ⲑⲁⲛⲁⲧⲟⲛ ⲩ̀ⲡⲟⲙⲓⲛⲉ: ⲕⲉ ⲉ̀ⲅⲓⲣⲉ ⲧⲟⲩⲥ ⲧⲉⲑⲛⲉⲱ̀ⲟ̀: ⲧⲁⲥ ⲉⲛ ⲧⲏ ⲉⲛⲇⲟⲝⲱ Ⲁ̀ⲛⲁⲥⲧⲁⲥⲓ ⲁⲩⲧⲟⲩ"
    result = break_words(lyrics)
    print(json.dumps(result, ensure_ascii=False))