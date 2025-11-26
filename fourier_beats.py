import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment
import tempfile
import os

def apply_phone_filter(input_file, output_file, 
                       low_freq=300, high_freq=3000, enhancement_factor=1.0):
    """
    模拟电话音效：仅保留特定频段并可增强该频段。
    :param input_file: 输入音频文件路径
    :param output_file: 处理后音频文件路径
    :param low_freq: 低频截止
    :param high_freq: 高频截止
    :param enhancement_factor: 增强中间频段的倍数
    """
    y, sr = librosa.load(input_file, sr=48000)
    Y = np.fft.fft(y)
    freq = np.fft.fftfreq(len(y), d=1/sr)
    
    band_mask = (np.abs(freq) < low_freq) | (np.abs(freq) > high_freq)
    Y[band_mask] = 0
    
    mid_band_mask = (np.abs(freq) >= low_freq) & (np.abs(freq) <= high_freq)
    Y[mid_band_mask] *= enhancement_factor
    
    y_new = np.fft.ifft(Y)
    y_new = np.real(y_new)
    sf.write(output_file, y_new, sr)

def apply_dizzy_effect(input_file, output_file, 
                       delay_seconds=0.05, decay_factor=0.5):
    """
    添加眩晕效果：振幅周期性变化。
    :param input_file: 输入音频文件路径
    :param output_file: 处理后音频文件路径
    :param delay_seconds: 音频延迟时间（秒）
    :param decay_factor: 音频衰减系数
    """
    y, sr = librosa.load(input_file, sr=48000)
    Y = np.fft.fft(y)
    freq = np.fft.fftfreq(len(y), d=1/sr)
    
    delay_samples = int(delay_seconds * sr)
    Y_echo = np.roll(Y, delay_samples) * decay_factor
    Y += Y_echo
    
    y_new = np.fft.ifft(Y)
    y_new = np.real(y_new)
    sf.write(output_file, y_new, sr)

def apply_cut_frequencies(input_file, output_file, cut_freq=10, half_width=3.0):
    """
    移除特定倍数的频率（带状滤波）。
    :param input_file: 输入音频文件路径
    :param output_file: 处理后音频文件路径
    :param cut_freq: 需要移除的频率间隔
    :param half_width: 允许保留的频率范围
    """
    y, sr = librosa.load(input_file, sr=48000)
    Y = np.fft.fft(y)
    freq = np.fft.fftfreq(len(y), d=1/sr)
    
    for i in range(len(Y)):
        f = abs(freq[i])
        remainder = f % cut_freq
        if remainder < half_width or remainder > (cut_freq - half_width):
            Y[i] = 0
    
    y_new = np.fft.ifft(Y)
    y_new = np.real(y_new)
    sf.write(output_file, y_new, sr)

def swap_beats(input_file, output_file):
    """
    交换每组的第2和第4拍，以产生新的节奏感。
    :param input_file: 输入音频文件路径
    :param output_file: 处理后音频文件路径
    """
    audio_segment = AudioSegment.from_file(input_file)
    bit_depth = audio_segment.sample_width * 8
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
        audio_segment.export(wav_path, format="wav", parameters=["-acodec", "pcm_s{}le".format(bit_depth)])
    
    audio, sr = sf.read(wav_path, always_2d=True, dtype='float32')
    audio = audio.T
    os.remove(wav_path)
    
    y_mono = librosa.to_mono(audio) if audio.shape[0] == 2 else audio[0]
    tempo, beat_frames = librosa.beat.beat_track(y=y_mono, sr=sr, units="samples")
    
    segments = []
    crossfade_duration = 512  # 交叉渐变时间
    total_samples = audio.shape[1]
    
    for i in range(len(beat_frames)):
        start = max(0, beat_frames[i] - crossfade_duration//2)
        end = beat_frames[i+1] + crossfade_duration//2 if i < len(beat_frames)-1 else total_samples
        segment = audio[:, start:end]
        
        if i > 0:
            fade_in = np.linspace(0, 1, crossfade_duration)
            segment[:, :crossfade_duration] *= fade_in
            prev_segment[:, -crossfade_duration:] *= (1 - fade_in)
            segments[-1] = prev_segment
        
        segments.append(segment)
        prev_segment = segment.copy()
    
    new_segments = []
    for i in range(0, len(segments), 4):
        group = segments[i:i+4]
        if len(group) >= 4:
            group[1], group[3] = group[3].copy(), group[1].copy()
        new_segments.extend(group)
    
    processed_audio = np.concatenate(new_segments, axis=1)
    
    if output_file.lower().endswith('.wav'):
        sf.write(output_file, processed_audio.T, sr, subtype=f'PCM_{bit_depth}')
    elif output_file.lower().endswith('.mp3'):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_wav = tmp.name
            sf.write(tmp_wav, processed_audio.T, sr, subtype=f'PCM_{bit_depth}')
        AudioSegment.from_wav(tmp_wav).export(output_file, format='mp3', bitrate='320k', parameters=["-ar", str(sr), "-q:a", "0"])
        os.remove(tmp_wav)
    else:
        raise ValueError("Unsupported format")

if __name__ == "__main__":
    input_path = "C:\\Users\\26063\\Downloads\\CloudMusic\\milet - Anytime Anywhere.mp3"
    output_path = "output.mp3"
    
    # 应用各种音频处理效果
    # apply_phone_filter(input_path, "phone_filter_output.mp3")
    apply_dizzy_effect(input_path, "dizzy_effect_output.mp3")
    apply_cut_frequencies(input_path, "cut_frequencies_output.mp3")
    # swap_beats(input_path, output_path)
    print("处理完成！")