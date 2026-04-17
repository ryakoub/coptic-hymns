import json

def break_words(lyrics):
    res = []
    for word in lyrics.split():
        line = {"text": word, "start": 0, "end": 0}
        res.append(line)
    return res

if __name__ == "__main__":
    lyrics = "Ⲉⲃⲟⲗ ϩⲓⲧⲉⲛ ⲡⲉϥⲥ̀ⲧⲁⲩⲣⲟⲥ: ⲛⲉⲙ ⲧⲉϥⲁ̀ⲛⲁⲥⲧⲁⲥⲓⲥ ⲉⲑⲟⲁⲃ: ⲁϥⲧⲁⲥⲑⲟ ⲙ̀ⲡⲓⲣⲱⲙⲓ ⲛ̀ⲕⲉⲥⲟⲡ: ⲉ̀Ϧⲟⲩⲛ ⲉ̀ⲡⲓⲡⲁⲣⲁⲇⲓⲥⲟⲥ"
    result = break_words(lyrics)
    print("[")
    for i, obj in enumerate(result):
        line = json.dumps(obj, ensure_ascii=False)
        if i < len(result) - 1:
            print(f"  {line},")
        else:
            print(f"  {line}")
    print("]")