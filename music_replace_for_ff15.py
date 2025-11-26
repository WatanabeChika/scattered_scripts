import subprocess

original_path = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY XV/datas/sound/resources/20000music/jp"

def rpc_for_FF1():
    # 替换最终幻想1的音乐，共9首
    goal_path = "D:/LoveLive/莲之空女学院学园偶像俱乐部"
    dic = {"bgm_car_ff1ar_01.win.sab": "单曲/[2023.03.29] 莲之空女学院学园偶像俱乐部 - Dream Believers/01. Dream Believers.flac",
           "bgm_car_ff1ar_02.win.sab": "单曲/[2023.03.29] 莲之空女学院学园偶像俱乐部 - Dream Believers/02. On your mark.flac",
           "bgm_car_ff1ar_03.win.sab": "单曲/[2023.03.29] 莲之空女学院学园偶像俱乐部 - Dream Believers/03. 水彩世界.flac",
           "bgm_car_ff1ar_04.win.sab": "单曲/[2023.03.29] 莲之空女学院学园偶像俱乐部 - Dream Believers/04. AWOKE.flac",
           "bgm_car_ff1ar_05.win.sab": "单曲/[2023.03.29] 莲之空女学院学园偶像俱乐部 - Dream Believers/05. ド！ド！ド！.flac",
           "bgm_car_ff1ar_06.win.sab": "单曲/[2023.03.29] 莲之空女学院学园偶像俱乐部 - Dream Believers/06. 永遠のEuphoria.flac",
           "bgm_car_ff1ar_07.win.sab": "小组曲/スリーズブーケ/[2023.04.26] スリーズブーケ - Reflection in the mirror/01. Reflection in the mirror.flac",
           "bgm_car_ff1ar_08.win.sab": "小组曲/スリーズブーケ/[2023.04.26] スリーズブーケ - Reflection in the mirror/02. フォーチュンムービー.flac",
           "bgm_car_ff1ar_09.win.sab": "小组曲/スリーズブーケ/[2023.04.26] スリーズブーケ - Reflection in the mirror/03. Mix shake!!.flac"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF2():
    # 替换最终幻想2的音乐，共11首
    goal_path = "D:/LoveLive/莲之空女学院学园偶像俱乐部"
    dic = {"bgm_car_ff2ar_01.win.sab": "小组曲/DOLLCHESTRA/[2023.04.26] DOLLCHESTRA - Sparkly Spot/01. Sparkly Spot.flac",
           "bgm_car_ff2ar_02.win.sab": "小组曲/DOLLCHESTRA/[2023.04.26] DOLLCHESTRA - Sparkly Spot/02. ツキマカセ.flac",
           "bgm_car_ff2ar_03.win.sab": "小组曲/DOLLCHESTRA/[2023.04.26] DOLLCHESTRA - Sparkly Spot/03. 希望的プリズム.flac",
           "bgm_car_ff2ar_04.win.sab": "单曲/[2023.06.14] スリーズブーケDOLLCHESTRA - Holiday∞Holiday／Tragic Drops/01. 謳歌爛漫.flac",
           "bgm_car_ff2ar_05.win.sab": "单曲/[2023.06.14] スリーズブーケDOLLCHESTRA - Holiday∞Holiday／Tragic Drops/02. スケイプゴート.flac",
           "bgm_car_ff2ar_06.win.sab": "单曲/[2023.06.14] スリーズブーケDOLLCHESTRA - Holiday∞Holiday／Tragic Drops/03. Holiday∞Holiday.flac",
           "bgm_car_ff2ar_07.win.sab": "单曲/[2023.06.14] スリーズブーケDOLLCHESTRA - Holiday∞Holiday／Tragic Drops/04. Tragic Drops.flac",
           "bgm_car_ff2ar_08.win.sab": "小组曲/スリーズブーケ/[2023.08.09] スリーズブーケ - 眩耀夜行/01. DEEPNESS.flac",
           "bgm_car_ff2ar_09.win.sab": "小组曲/スリーズブーケ/[2023.08.09] スリーズブーケ - 眩耀夜行/02. Kawaii no susume.flac",
           "bgm_car_ff2ar_10.win.sab": "小组曲/スリーズブーケ/[2023.08.09] スリーズブーケ - 眩耀夜行/03. 眩耀夜行.flac",
           "bgm_car_ff2ar_11.win.sab": "小组曲/DOLLCHESTRA/[2023.08.09] DOLLCHESTRA - Mirage Voyage/02. ジブンダイアリー.flac"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF3():
    # 替换最终幻想3的音乐，共13首
    goal_path = "D:/LoveLive/莲之空女学院学园偶像俱乐部"
    dic = {"bgm_car_ff3ar_01.win.sab": "小组曲/DOLLCHESTRA/[2023.08.09] DOLLCHESTRA - Mirage Voyage/03. Mirage Voyage.flac",
           "bgm_car_ff3ar_02.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/01. 夏めきペイン.flac",
           "bgm_car_ff3ar_03.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/02. Yup! Yup! Yup!.flac",
           "bgm_car_ff3ar_04.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/03. ココン東西.flac",
           "bgm_car_ff3ar_05.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/04. 残陽.flac",
           "bgm_car_ff3ar_06.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/05. 青春の輪郭.flac",
           "bgm_car_ff3ar_07.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/06. ハクチューアラモード.flac",
           "bgm_car_ff3ar_08.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/07. Dear my future.flac",
           "bgm_car_ff3ar_09.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/08. パラレルダンサー.flac",
           "bgm_car_ff3ar_10.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/09. 明日の空の僕たちへ.flac",
           "bgm_car_ff3ar_11.win.sab": "单曲/[2023.09.20] 莲之空女学院学园偶像俱乐部 - 夏めきペイン/10. Legato.flac",
           "bgm_car_ff3ar_12.win.sab": "小组曲/スリーズブーケ/[2023.11.15] スリーズブーケ - 素顔のピクセル/01. 素顔のピクセル.flac",
           "bgm_car_ff3ar_13.win.sab": "小组曲/スリーズブーケ/[2023.11.15] スリーズブーケ - 素顔のピクセル/02. シュガーメルト.flac"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF4():
    # 替换最终幻想4的音乐，共12首
    goal_path = "D:/LoveLive/莲之空女学院学园偶像俱乐部"
    dic = {"bgm_car_ff4ar_01.win.sab": "小组曲/スリーズブーケ/[2023.11.15] スリーズブーケ - 素顔のピクセル/03. 千変万華.flac",
           "bgm_car_ff4ar_02.win.sab": "小组曲/DOLLCHESTRA/[2023.11.22] DOLLCHESTRA - Take It Over/01. Take It Over.flac",
           "bgm_car_ff4ar_03.win.sab": "小组曲/DOLLCHESTRA/[2023.11.22] DOLLCHESTRA - Take It Over/02. 飴色.flac",
           "bgm_car_ff4ar_04.win.sab": "小组曲/DOLLCHESTRA/[2023.11.22] DOLLCHESTRA - Take It Over/03. KNOT.flac",
           "bgm_car_ff4ar_05.win.sab": "小组曲/みらくらぱーく！/[2023.11.29] みらくらぱーく！ - アイデンティティ/01. アイデンティティ.flac",
           "bgm_car_ff4ar_06.win.sab": "小组曲/みらくらぱーく！/[2023.11.29] みらくらぱーく！ - アイデンティティ/02. 天才なのかもしれない.flac",
           "bgm_car_ff4ar_07.win.sab": "小组曲/みらくらぱーく！/[2023.11.29] みらくらぱーく！ - アイデンティティ/03. ノンフィクションヒーローショー.flac",
           "bgm_car_ff4ar_08.win.sab": "单曲/[2024.01.17] 莲之空女学院学园偶像俱乐部 - Link to the FUTURE/01. Trick  Cute.flac",
           "bgm_car_ff4ar_09.win.sab": "单曲/[2024.01.17] 莲之空女学院学园偶像俱乐部 - Link to the FUTURE/02. ツバサ・ラ・リベルテ.flac",
           "bgm_car_ff4ar_10.win.sab": "单曲/[2024.01.17] 莲之空女学院学园偶像俱乐部 - Link to the FUTURE/03. Link to the FUTURE.flac",
           "bgm_car_ff4ar_11.win.sab": "单曲/[2024.02.14] スリーズブーケDOLLCHESTRAみらくらぱーく！ - Special Thanks／青とシャボン／ミルク/01. Special Thanks.flac",
           "bgm_car_ff4ar_12.win.sab": "单曲/[2024.02.14] スリーズブーケDOLLCHESTRAみらくらぱーく！ - Special Thanks／青とシャボン／ミルク/02. 青とシャボン.flac"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF5():
    # 替换最终幻想5的音乐，共16首
    goal_path = "D:/LoveLive"
    dic = {"bgm_car_ff5or_01.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.02.14] スリーズブーケDOLLCHESTRAみらくらぱーく！ - Special Thanks／青とシャボン／ミルク/03. ミルク.flac",
           "bgm_car_ff5or_02.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.03.20] るりのとゆかいなつづりたちかほめぐ♡じぇらーと蓮ノ休日 - Colorfulness／ハッピー至上主義！／Pleasure Feather/01. Colorfulness.flac",
           "bgm_car_ff5or_03.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.03.20] るりのとゆかいなつづりたちかほめぐ♡じぇらーと蓮ノ休日 - Colorfulness／ハッピー至上主義！／Pleasure Feather/02. ハッピー至上主義！.flac",
           "bgm_car_ff5or_04.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.03.20] るりのとゆかいなつづりたちかほめぐ♡じぇらーと蓮ノ休日 - Colorfulness／ハッピー至上主義！／Pleasure Feather/03. Pleasure Feather.flac",
           "bgm_car_ff5or_05.win.sab": "莲之空女学院学园偶像俱乐部/小组曲/みらくらぱーく！/[2024.03.27] みらくらぱーく！ - 以心☆電信/01. 以心☆電信.flac",
           "bgm_car_ff5or_06.win.sab": "莲之空女学院学园偶像俱乐部/小组曲/みらくらぱーく！/[2024.03.27] みらくらぱーく！ - 以心☆電信/02. BANG YOU グラビティ.flac",
           "bgm_car_ff5or_07.win.sab": "莲之空女学院学园偶像俱乐部/小组曲/みらくらぱーく！/[2024.03.27] みらくらぱーく！ - 以心☆電信/03. マハラジャンボリー.flac",
           "bgm_car_ff5or_08.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.04.03] 莲之空女学院学园偶像俱乐部 - 抱きしめる花びら/01. 抱きしめる花びら.flac",
           "bgm_car_ff5or_09.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.04.03] 莲之空女学院学园偶像俱乐部 - 抱きしめる花びら/02. STEP UP !.flac",
           "bgm_car_ff5or_10.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.04.17] 莲之空女学院学园偶像俱乐部 - Dream Believers (104期 Ver.)/03. アオクハルカ.flac",
           "bgm_car_ff5or_11.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.04.17] 莲之空女学院学园偶像俱乐部 - Dream Believers (104期 Ver.)/04. レディバグ.flac",
           "bgm_car_ff5or_12.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.04.17] 莲之空女学院学园偶像俱乐部 - Dream Believers (104期 Ver.)/05. みらくりえーしょん.flac",
           "bgm_car_ff5or_13.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.07.17] 莲之空女学院学园偶像俱乐部 - Bloom the smile, Bloom the dream!/01. Bloom the smile, Bloom the dream!.flac",
           "bgm_car_ff5or_14.win.sab": "莲之空女学院学园偶像俱乐部/单曲/[2024.07.17] 莲之空女学院学园偶像俱乐部 - Bloom the smile, Bloom the dream!/02. 365 Days.flac",
           "bgm_car_ff5or_15.win.sab": "Aqours/小组曲/わいわいわい/[2024.05.08] わいわいわい - peace piece pizza/01. peace piece pizza.flac",
           "bgm_car_ff5or_16.win.sab": "Aqours/小组曲/わいわいわい/[2024.05.08] わいわいわい - peace piece pizza/02. U-CYU.flac"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF6():
    # 替换最终幻想6的音乐，共12首
    goal_path = "C:/Users/26063/Downloads/CloudMusic"
    dic = {"bgm_car_ff6or_01.win.sab": "Lyn - Wake Up, Get Up, Get Out There.mp3",
           "bgm_car_ff6or_02.win.sab": "Lyn - Life Will Change.mp3",
           "bgm_car_ff6or_03.win.sab": "目黒将司,小宮知子 - 全ての人の魂の詩.mp3",
           "bgm_car_ff6or_04.win.sab": "目黒将司 - Will Power.mp3",
           "bgm_car_ff6or_05.win.sab": "目黒将司 - 王と王妃と奴隷.mp3",
           "bgm_car_ff6or_06.win.sab": "Lyn - Last Surprise.mp3",
           "bgm_car_ff6or_07.win.sab": "目黒将司 - Layer Cake.mp3",
           "bgm_car_ff6or_08.win.sab": "Lyn - Beneath the Mask.mp3",
           "bgm_car_ff6or_09.win.sab": "Lyn - Tokyo Daylight.mp3",
           "bgm_car_ff6or_10.win.sab": "目黒将司 - A Woman.mp3",
           "bgm_car_ff6or_11.win.sab": "Lyn - Beneath the Mask -rain-.mp3",
           "bgm_car_ff6or_12.win.sab": "目黒将司 - Price.mp3"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF7():
    # 替换最终幻想7的音乐，共14首
    goal_path = "C:/Users/26063/Downloads/CloudMusic"
    dic = {"bgm_car_ff7or_01.win.sab": "目黒将司 - 母のいた日々.mp3",
           "bgm_car_ff7or_02.win.sab": "Lyn - The Whims of Fate.mp3",
           "bgm_car_ff7or_03.win.sab": "目黒将司 - 方舟.mp3",
           "bgm_car_ff7or_04.win.sab": "Lyn - Rivers In the Desert.mp3",
           "bgm_car_ff7or_05.win.sab": "目黒将司 - 自由と安心.mp3",
           "bgm_car_ff7or_06.win.sab": "目黒将司 - Jaldabaoth.mp3",
           "bgm_car_ff7or_07.win.sab": "目黒将司 - Our Beginning.mp3",
           "bgm_car_ff7or_08.win.sab": "Lyn - 星と僕らと.mp3",
           "bgm_car_ff7or_09.win.sab": "Lyn - Colors Flying High -opening movie version-.mp3",
           "bgm_car_ff7or_10.win.sab": "Lyn - Take Over.mp3",
           "bgm_car_ff7or_11.win.sab": "Lyn - No More What Ifs.mp3",
           "bgm_car_ff7or_12.win.sab": "小西利樹 - wish come true.mp3",
           "bgm_car_ff7or_13.win.sab": "目黒将司 - Gentle Madman.mp3",
           "bgm_car_ff7or_14.win.sab": "Lyn - I believe.mp3"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF8():
    # 替换最终幻想8的音乐，共17首
    goal_path = "C:/Users/26063/Downloads/CloudMusic"
    dic = {"bgm_car_ff8or_01.win.sab": "目黒将司 - Keep Your Faith.mp3",
           "bgm_car_ff8or_02.win.sab": "Lyn - Throw Away Your Mask.mp3",
           "bgm_car_ff8or_03.win.sab": "Lyn - 僕らの光.mp3",
           "bgm_car_ff8or_04.win.sab": "ナユタン星人,MORE MORE JUMP！,初音ミク - モア！ジャンプ！モア！ (feat. 花里みのり桐谷遥桃井愛莉日野森雫初音ミク).mp3",
           "bgm_car_ff8or_05.win.sab": "鏡音リン,鏡音レン,ギガP - 劣等上等.mp3",
           "bgm_car_ff8or_06.win.sab": "かいりきベア,初音ミク - バグ.mp3",
           "bgm_car_ff8or_07.win.sab": "wowaka,初音ミク - アンノウン・マザーグース.mp3",
           "bgm_car_ff8or_08.win.sab": "livetune,初音ミク - Hand in Hand.mp3",
           "bgm_car_ff8or_09.win.sab": "40mP,初音ミク - からくりピエロ.mp3",
           "bgm_car_ff8or_10.win.sab": "鏡音リン,みきとP - ロキ.mp3",
           "bgm_car_ff8or_11.win.sab": "すりぃ,鏡音レン - テレキャスタービーボーイ.mp3",
           "bgm_car_ff8or_12.win.sab": "ポリスピカデリー,初音ミク - Chaotic Love Revolution.mp3",
           "bgm_car_ff8or_13.win.sab": "Giga,鏡音リン,巡音ルカ - drop pop candy.mp3",
           "bgm_car_ff8or_14.win.sab": "すりぃ,25時、ナイトコードで。,鏡音リン - 限りなく灰色へ (feat. 宵崎奏朝比奈まふゆ東雲絵名暁山瑞希鏡音リン).mp3",
           "bgm_car_ff8or_15.win.sab": "ゆうゆ,初音ミク - 深海少女.mp3",
           "bgm_car_ff8or_16.win.sab": "DECO27,TeddyLoid,初音ミク - 乙女解剖 (TeddyLoid Alllies Remix).mp3",
           "bgm_car_ff8or_17.win.sab": "雄之助,CircusP,初音ミク - Intergalactic Bound (feat. Hatsune Miku).mp3"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF9():
    # 替换最终幻想9的音乐，共20首
    goal_path = "C:/Users/26063/Downloads/CloudMusic"
    dic = {"bgm_car_ff9or_01.win.sab": "MyGO!!!!! - 迷星叫.mp3",
           "bgm_car_ff9or_02.win.sab": "MyGO!!!!! - 名無声.mp3",
           "bgm_car_ff9or_03.win.sab": "MyGO!!!!! - 音一会.mp3",
           "bgm_car_ff9or_04.win.sab": "MyGO!!!!! - 潜在表明.mp3",
           "bgm_car_ff9or_05.win.sab": "MyGO!!!!! - 影色舞.mp3",
           "bgm_car_ff9or_06.win.sab": "MyGO!!!!! - 壱雫空.mp3",
           "bgm_car_ff9pl_02.win.sab": "MyGO!!!!! - 栞.mp3",
           "bgm_car_ff9or_08.win.sab": "MyGO!!!!! - 焚音打.mp3",
           "bgm_car_ff9or_09.win.sab": "MyGO!!!!! - 碧天伴走.mp3",
           "bgm_car_ff9or_10.win.sab": "MyGO!!!!! - 歌いましょう鳴らしましょう.mp3",
           "bgm_car_ff9or_11.win.sab": "MyGO!!!!! - 春日影 (MyGO!!!!! ver.).mp3",
           "bgm_car_ff9or_12.win.sab": "MyGO!!!!! - 詩超絆.mp3",
           "bgm_car_ff9or_13.win.sab": "MyGO!!!!! - 迷路日々.mp3",
           "bgm_car_ff9or_14.win.sab": "MyGO!!!!! - 無路矢.mp3",
           "bgm_car_ff9or_15.win.sab": "MyGO!!!!! - 処救生.mp3",
           "bgm_car_ff9pl_03.win.sab": "MyGO!!!!! - 輪符雨.mp3",
           "bgm_car_ff9or_17.win.sab": "MyGO!!!!! - 砂寸奏.mp3",
           "bgm_car_ff9or_18.win.sab": "MyGO!!!!! - 回層浮.mp3",
           "bgm_car_ff9or_19.win.sab": "MyGO!!!!! - 端程山.mp3",
           "bgm_car_ff9or_20.win.sab": "MyGO!!!!! - 孤壊牢.mp3"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)

def rpc_for_FF10():
    # 替换最终幻想10的音乐，共15首
    goal_path = "C:/Users/26063/Downloads/CloudMusic"
    dic = {"bgm_car_ff10or_01.win.sab": "てにをは,初音ミク - ザムザ.mp3",
           "bgm_car_ff10or_02.win.sab": "かいりきベア,初音ミク - メロメロイド (feat. 初音ミク).mp3",
           "bgm_car_ff10or_03.win.sab": "Giga,可不 - CH4NGE (feat. 可不).mp3",
           "bgm_car_ff10or_04.win.sab": "DECO27,初音ミク - 妄想感傷代償連盟.mp3",
           "bgm_car_ff10or_05.win.sab": "ピノキオピー,初音ミク - 魔法少女とチョコレゐト.mp3",
           "bgm_car_ff10or_06.win.sab": "ピノキオピー,初音ミク - ラヴィット.mp3",
           "bgm_car_ff10or_07.win.sab": "DECO27,初音ミク - 乙女解剖.mp3",
           "bgm_car_ff10or_08.win.sab": "DECO27,初音ミク - ハオ.mp3",
           "bgm_car_ff10or_09.win.sab": "ピノキオピー,初音ミク - 神っぽいな.mp3",
           "bgm_car_ff10or_10.win.sab": "ナユタン星人,000 - 光線チューニング.mp3",
           "bgm_car_ff10or_11.win.sab": "kanaria,星街すいせい - レクイエム (feat. 星街すいせい).mp3",
           "bgm_car_ff10or_12.win.sab": "DECO27,初音ミク - ヴァンパイア.mp3",
           "bgm_car_ff10or_13.win.sab": "DECO27,初音ミク - アンドロイドガール.mp3",
           "bgm_car_ff10or_14.win.sab": "かいりきベア,初音ミク - ダーリンダンス.mp3",
           "bgm_car_ff10or_15.win.sab": "kanaria,GUMI - 酔いどれ知らず.mp3"}
    for i in dic:
        command = 'cmd /c "FFXVRT.exe -i \"{}\" -r \"{}\""'.format(original_path + "/" + i, goal_path + "/" + dic[i])
        subprocess.run(command, shell=True)
