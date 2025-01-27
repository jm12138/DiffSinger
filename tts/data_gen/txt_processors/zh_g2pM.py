import re
import jieba
from pypinyin import pinyin, Style
from data_gen.data_gen_utils import PUNCS
from tts.data_gen.txt_processors import zh
from g2pM import G2pM
from utils.phoneme_utils import build_g2p_dictionary


_initialized = False
_ALL_CONSONANTS_SET = set()
_ALL_VOWELS_SET = set()


def _initialize_consonants_and_vowels():
    # Currently we only support two-part consonant-vowel phoneme systems.
    for _ph_list in build_g2p_dictionary().values():
        _ph_count = len(_ph_list)
        if _ph_count == 0 or _ph_list[0] in ['AP', 'SP']:
            continue
        elif len(_ph_list) == 1:
            _ALL_VOWELS_SET.add(_ph_list[0])
        else:
            _ALL_CONSONANTS_SET.add(_ph_list[0])
            _ALL_VOWELS_SET.add(_ph_list[1])


def get_all_consonants():
    global _initialized
    if not _initialized:
        _initialize_consonants_and_vowels()
        _initialized = True
    return sorted(_ALL_CONSONANTS_SET)


def get_all_vowels():
    global _initialized
    if not _initialized:
        _initialize_consonants_and_vowels()
        _initialized = True
    return sorted(_ALL_VOWELS_SET)


class TxtProcessor(zh.TxtProcessor):
    model = G2pM()

    @staticmethod
    def sp_phonemes():
        return ['|', '#']

    @classmethod
    def process(cls, txt, pre_align_args):
        txt = cls.preprocess_text(txt)
        ph_list = cls.model(txt, tone=pre_align_args['use_tone'], char_split=True)
        seg_list = '#'.join(jieba.cut(txt))
        assert len(ph_list) == len([s for s in seg_list if s != '#']), (ph_list, seg_list)

        # 加入词边界'#'
        ph_list_ = []
        seg_idx = 0
        for p in ph_list:
            p = p.replace("u:", "v")
            if seg_list[seg_idx] == '#':
                ph_list_.append('#')
                seg_idx += 1
            else:
                ph_list_.append("|")
            seg_idx += 1
            if re.findall('[\u4e00-\u9fff]', p):
                if pre_align_args['use_tone']:
                    p = pinyin(p, style=Style.TONE3, strict=True)[0][0]
                    if p[-1] not in ['1', '2', '3', '4', '5']:
                        p = p + '5'
                else:
                    p = pinyin(p, style=Style.NORMAL, strict=True)[0][0]

            finished = False
            consonants = get_all_consonants()
            if len([c.isalpha() for c in p]) > 1:
                for shenmu in consonants:
                    if p.startswith(shenmu) and not p.lstrip(shenmu).isnumeric():
                        ph_list_ += [shenmu, p.lstrip(shenmu)]
                        finished = True
                        break
            if not finished:
                ph_list_.append(p)

        ph_list = ph_list_

        # 去除静音符号周围的词边界标记 [..., '#', ',', '#', ...]
        sil_phonemes = list(PUNCS) + TxtProcessor.sp_phonemes()
        ph_list_ = []
        for i in range(0, len(ph_list), 1):
            if ph_list[i] != '#' or (ph_list[i - 1] not in sil_phonemes and ph_list[i + 1] not in sil_phonemes):
                ph_list_.append(ph_list[i])
        ph_list = ph_list_
        return ph_list, txt


if __name__ == '__main__':
    phs, txt = TxtProcessor.process('他来到了，网易杭研大厦', {'use_tone': True})
    print(phs)
