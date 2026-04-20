from __future__ import annotations

import argparse
import math
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np
from tqdm.auto import tqdm


@dataclass
class FrameItem:
    image: np.ndarray
    frame_index: int
    timestamp: float


def parse_time_to_seconds(text: str) -> float:
    text = text.strip()
    if ":" not in text:
        return float(text)
    hh, mm, ss = text.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


def seconds_to_hhmmss(seconds: float) -> str:
    hh = int(seconds // 3600)
    mm = int((seconds % 3600) // 60)
    ss = seconds - hh * 3600 - mm * 60
    return f"{hh:02d}:{mm:02d}:{ss:09.6f}"


def probe_video_fps(video_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    if "/" in out:
        return float(Fraction(out))
    return float(out)


def snap_to_frame_time(time_sec: float, fps: float) -> tuple[int, float]:
    idx = int(round(time_sec * fps))
    return idx, idx / fps


def resize_keep_ratio(image: np.ndarray, target_width: int) -> np.ndarray:
    if image.shape[1] <= target_width:
        return image
    scale = target_width / float(image.shape[1])
    target_height = max(1, int(round(image.shape[0] * scale)))
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)


def blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def estimate_motion(prev_gray: np.ndarray, curr_gray: np.ndarray) -> tuple[float, float]:
    shift, response = cv2.phaseCorrelate(
        prev_gray.astype(np.float32), curr_gray.astype(np.float32)
    )
    dx, dy = shift
    return math.hypot(dx, dy), float(response)


def extract_keyframes(
    video_path: str,
    start_frame: int,
    end_frame: int,
    video_fps: float,
    sample_fps: float,
    min_blur: float,
    min_motion_px: float,
    force_keep_seconds: float,
    preview_width: int,
    max_keyframes: int,
) -> list[FrameItem]:
    total_decode_frames = max(1, end_frame - start_frame + 1)

    def sample_candidates(step: int) -> list[FrameItem]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        pbar = tqdm(
            total=total_decode_frames,
            desc=f"decode(step={step})",
            unit="f",
            dynamic_ncols=True,
            leave=False,
        )

        sampled: list[FrameItem] = []
        frame_idx = start_frame
        next_pick = start_frame
        while frame_idx <= end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx >= next_pick:
                sampled.append(
                    FrameItem(
                        image=frame.copy(),
                        frame_index=frame_idx,
                        timestamp=frame_idx / video_fps,
                    )
                )
                next_pick += step
            frame_idx += 1
            pbar.update(1)
        pbar.close()
        cap.release()
        return sampled

    def filter_candidates(
        candidates: list[FrameItem],
        blur_thr: float,
        motion_thr: float,
        keep_gap_sec: float,
    ) -> list[FrameItem]:
        if len(candidates) <= 2:
            return candidates

        pbar = tqdm(
            total=max(1, len(candidates) - 1),
            desc="keyframe-filter",
            unit="f",
            dynamic_ncols=True,
            leave=False,
        )
        kept: list[FrameItem] = [candidates[0]]
        last_kept_preview = cv2.cvtColor(
            resize_keep_ratio(candidates[0].image, preview_width), cv2.COLOR_BGR2GRAY
        )
        last_kept_ts = candidates[0].timestamp
        last_idx = len(candidates) - 1

        for i, item in enumerate(candidates[1:], start=1):
            preview = resize_keep_ratio(item.image, preview_width)
            gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)

            # Always retain the final sampled frame if we still have too few keyframes.
            if i == last_idx and len(kept) < 2:
                kept.append(item)
                last_kept_preview = gray
                last_kept_ts = item.timestamp
                pbar.update(1)
                continue

            if blur_score(gray) < blur_thr:
                pbar.update(1)
                continue

            motion_px, response = estimate_motion(last_kept_preview, gray)
            elapsed = item.timestamp - last_kept_ts
            if motion_px >= motion_thr or (
                elapsed >= keep_gap_sec and response < 0.20
            ):
                kept.append(item)
                last_kept_preview = gray
                last_kept_ts = item.timestamp
            pbar.update(1)

        pbar.close()

        if len(kept) < 2 and len(candidates) >= 2:
            kept = [candidates[0], candidates[-1]]
        return kept

    def limit_keyframes(items: list[FrameItem], limit: int) -> list[FrameItem]:
        if len(items) <= limit:
            return items
        picks = np.linspace(0, len(items) - 1, limit).astype(int)
        return [items[i] for i in picks]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    step = max(1, int(round(video_fps / sample_fps)))
    cap.release()
    candidates = sample_candidates(step=step)

    # Short clips or very low sample-fps may produce too few sampled frames.
    # Automatically fallback to frame-by-frame sampling before giving up.
    if len(candidates) < 2:
        candidates = sample_candidates(step=1)

    if len(candidates) < 2:
        raise RuntimeError("Not enough frames in selected segment after decoding.")

    keyframes = filter_candidates(
        candidates=candidates,
        blur_thr=min_blur,
        motion_thr=min_motion_px,
        keep_gap_sec=force_keep_seconds,
    )

    if len(keyframes) < 2:
        keyframes = filter_candidates(
            candidates=candidates,
            blur_thr=max(0.0, min_blur * 0.45),
            motion_thr=max(0.6, min_motion_px * 0.45),
            keep_gap_sec=max(0.15, force_keep_seconds * 0.5),
        )
        if len(keyframes) >= 2:
            print("[warn] Keyframe filter auto-relaxed for short/low-motion clip.")

    if len(keyframes) < 2:
        # Last fallback: keep all sampled frames to avoid false failure on short shots.
        keyframes = candidates
        print("[warn] Using all sampled frames because strict keyframe filtering was too aggressive.")

    keyframes = limit_keyframes(keyframes, max_keyframes)
    if len(keyframes) < 2:
        raise RuntimeError(
            "Not enough keyframes even after fallback. Try a slightly longer segment."
        )
    return keyframes


def feature_config() -> tuple[bool, int, float, int, int]:
    use_sift = hasattr(cv2, "SIFT_create")
    if use_sift:
        return True, cv2.NORM_L2, 0.72, 40, 30
    return False, cv2.NORM_HAMMING, 0.75, 30, 25


def compute_feature_pack(
    bgr: np.ndarray,
    use_sift: bool,
) -> tuple[np.ndarray, np.ndarray | None]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if use_sift:
        detector = cv2.SIFT_create(nfeatures=4000)
    else:
        detector = cv2.ORB_create(nfeatures=5000)
    kp, des = detector.detectAndCompute(gray, None)
    if not kp:
        return np.empty((0, 2), dtype=np.float32), None
    pts = np.float32([k.pt for k in kp])
    return pts, des


def estimate_homography_from_packs(
    prev_pack: tuple[np.ndarray, np.ndarray | None],
    curr_pack: tuple[np.ndarray, np.ndarray | None],
    norm: int,
    ratio: float,
    min_kp: int,
    min_good: int,
) -> np.ndarray | None:
    prev_pts, des1 = prev_pack
    curr_pts, des2 = curr_pack
    if des1 is None or des2 is None or len(prev_pts) < min_kp or len(curr_pts) < min_kp:
        return None

    matcher = cv2.BFMatcher(norm)
    knn = matcher.knnMatch(des1, des2, k=2)
    good = []
    for pair in knn:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance:
            good.append(m)
    if len(good) < min_good:
        return None

    src = np.float32([curr_pts[m.trainIdx] for m in good]).reshape(-1, 1, 2)
    dst = np.float32([prev_pts[m.queryIdx] for m in good]).reshape(-1, 1, 2)
    h, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if h is None or inliers is None:
        return None
    inlier_ratio = float(inliers.sum()) / max(1, len(inliers))
    if inlier_ratio < 0.22:
        return None
    return h


def build_soft_weight(shape: tuple[int, int], feather_radius: int) -> np.ndarray:
    h, w = shape
    src_mask = np.full((h, w), 255, dtype=np.uint8)
    k = max(3, feather_radius)
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    inner = cv2.erode(src_mask, kernel)
    dist = cv2.distanceTransform(inner, cv2.DIST_L2, 3)
    if float(dist.max()) <= 1e-6:
        return np.ones((h, w), dtype=np.float32)
    dist = dist / float(dist.max())
    return np.clip(dist, 0.05, 1.0).astype(np.float32)


def crop_valid_area(image: np.ndarray, weight: np.ndarray) -> np.ndarray:
    valid = (weight > 0.01).astype(np.uint8) * 255
    points = cv2.findNonZero(valid)
    if points is None:
        return image
    x, y, w, h = cv2.boundingRect(points)
    return image[y : y + h, x : x + w]


def stitch_panorama(
    keyframes: list[FrameItem],
    stitch_width: int,
    max_output_megapixels: float,
    feather_radius: int,
) -> tuple[np.ndarray, int]:
    stitch_start = time.perf_counter()
    images = [resize_keep_ratio(item.image, stitch_width) for item in keyframes]

    use_sift, norm, ratio, min_kp, min_good = feature_config()
    feat_start = time.perf_counter()
    features: list[tuple[np.ndarray, np.ndarray | None] | None] = [None] * len(images)
    feat_workers = min(max(1, os.cpu_count() or 1), len(images), 8)
    with tqdm(total=len(images), desc="feature-prep", unit="f", dynamic_ncols=True, leave=False) as feat_pbar:
        with ThreadPoolExecutor(max_workers=feat_workers) as executor:
            futures = {executor.submit(compute_feature_pack, img, use_sift): i for i, img in enumerate(images)}
            for future in as_completed(futures):
                idx = futures[future]
                features[idx] = future.result()
                feat_pbar.update(1)
    print(f"[time] feature precompute ({feat_workers} threads): {time.perf_counter() - feat_start:.2f}s")

    chain: list[np.ndarray] = [np.eye(3, dtype=np.float64)]  # i -> 0
    accepted = [images[0]]
    accepted_indices = [0]
    h_start = time.perf_counter()
    with tqdm(
        total=max(1, len(images) - 1),
        desc="homography",
        unit="f",
        dynamic_ncols=True,
        leave=False,
    ) as h_pbar:
        for i in range(1, len(images)):
            prev_idx = accepted_indices[-1]
            prev_pack = features[prev_idx]
            curr_pack = features[i]
            if prev_pack is None or curr_pack is None:
                h_pbar.update(1)
                continue
            h_curr_to_prev = estimate_homography_from_packs(
                prev_pack, curr_pack, norm, ratio, min_kp, min_good
            )
            if h_curr_to_prev is None:
                h_pbar.update(1)
                continue
            h_curr_to_0 = chain[-1] @ h_curr_to_prev
            chain.append(h_curr_to_0)
            accepted.append(images[i])
            accepted_indices.append(i)
            h_pbar.update(1)
    print(f"[time] homography chain: {time.perf_counter() - h_start:.2f}s")

    if len(accepted) < 2:
        raise RuntimeError("Cannot stitch: insufficient reliable frame matches.")

    # Use middle frame as reference to reduce long-chain distortion.
    ref_idx = len(accepted) // 2
    ref_inv = np.linalg.inv(chain[ref_idx])
    transforms = [ref_inv @ h for h in chain]  # i -> ref

    corners_all = []
    for img, h in zip(accepted, transforms):
        hh, ww = img.shape[:2]
        corners = np.array([[0, 0], [ww, 0], [ww, hh], [0, hh]], dtype=np.float32).reshape(
            -1, 1, 2
        )
        corners_all.append(cv2.perspectiveTransform(corners, h))
    all_pts = np.concatenate(corners_all, axis=0).reshape(-1, 2)

    min_x, min_y = np.min(all_pts, axis=0)
    max_x, max_y = np.max(all_pts, axis=0)
    out_w = max(1, int(math.ceil(float(max_x - min_x))))
    out_h = max(1, int(math.ceil(float(max_y - min_y))))

    max_pixels = max_output_megapixels * 1_000_000.0
    scale = 1.0
    if out_w * out_h > max_pixels:
        scale = math.sqrt(max_pixels / float(out_w * out_h))
        out_w = max(1, int(round(out_w * scale)))
        out_h = max(1, int(round(out_h * scale)))

    shift = np.array(
        [[1.0, 0.0, -float(min_x)], [0.0, 1.0, -float(min_y)], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    resize_h = np.array(
        [[scale, 0.0, 0.0], [0.0, scale, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64
    )

    # First-version style blending: weighted averaging across frames.
    # Improve seam quality by stronger edge falloff + mild overlap color balancing.
    acc = np.zeros((out_h, out_w, 3), dtype=np.float32)
    wsum = np.zeros((out_h, out_w), dtype=np.float32)
    coverage = np.zeros((out_h, out_w), dtype=np.float32)

    sharpness_values = []
    for img in accepted:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sharpness_values.append(blur_score(gray))
    sharpness_values = np.array(sharpness_values, dtype=np.float32)
    if float(sharpness_values.max()) > float(sharpness_values.min()):
        sharpness_norm = 0.85 + 0.30 * (
            (sharpness_values - sharpness_values.min())
            / (sharpness_values.max() - sharpness_values.min())
        )
    else:
        sharpness_norm = np.ones_like(sharpness_values, dtype=np.float32)

    weight_cache: dict[tuple[int, int], np.ndarray] = {}
    valid_cache: dict[tuple[int, int], np.ndarray] = {}
    for img in accepted:
        shape_key = (img.shape[0], img.shape[1])
        if shape_key not in weight_cache:
            weight_cache[shape_key] = build_soft_weight(shape_key, feather_radius)
            valid_cache[shape_key] = np.ones(shape_key, dtype=np.float32)

    def prepare_warp_pack(
        idx: int,
    ) -> tuple[int, tuple[int, int, int, int] | None, np.ndarray | None, np.ndarray | None, np.ndarray | None]:
        img = accepted[idx]
        h = transforms[idx]
        h_canvas = resize_h @ shift @ h
        warped = cv2.warpPerspective(
            img, h_canvas, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT
        )

        shape_key = (img.shape[0], img.shape[1])
        src_weight = weight_cache[shape_key]
        src_valid = valid_cache[shape_key]

        w = cv2.warpPerspective(
            src_weight,
            h_canvas,
            (out_w, out_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )
        valid_soft = cv2.warpPerspective(
            src_valid,
            h_canvas,
            (out_w, out_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )
        valid_mask = (valid_soft > 0.6).astype(np.float32)
        valid_u8 = (valid_mask * 255).astype(np.uint8)
        valid_u8 = cv2.erode(valid_u8, np.ones((3, 3), np.uint8), iterations=1)
        valid_mask = (valid_u8 > 0).astype(np.float32)

        score = (w * valid_mask * sharpness_norm[idx]).astype(np.float32)
        nz = np.argwhere(valid_mask > 0.5)
        if nz.size == 0:
            return idx, None, None, None, None
        y0, x0 = np.min(nz, axis=0)
        y1, x1 = np.max(nz, axis=0) + 1

        warped_roi = warped[y0:y1, x0:x1].astype(np.float32)
        score_roi = score[y0:y1, x0:x1]
        valid_roi = valid_mask[y0:y1, x0:x1]
        return idx, (int(y0), int(y1), int(x0), int(x1)), warped_roi, score_roi, valid_roi

    prep_start = time.perf_counter()
    workers = min(max(1, os.cpu_count() or 1), len(accepted), 8)
    batch_size = max(8, workers * 2)

    blend_start = time.perf_counter()
    prep_elapsed = 0.0
    blend_elapsed = 0.0
    with tqdm(total=len(accepted), desc="warp-prep", unit="f", dynamic_ncols=True, leave=False) as prep_pbar:
        with tqdm(total=len(accepted), desc="blend", unit="f", dynamic_ncols=True, leave=False) as blend_pbar:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for batch_start in range(0, len(accepted), batch_size):
                    batch_indices = list(range(batch_start, min(batch_start + batch_size, len(accepted))))

                    t0 = time.perf_counter()
                    futures = {
                        executor.submit(prepare_warp_pack, idx): idx for idx in batch_indices
                    }
                    batch_results: dict[
                        int,
                        tuple[
                            tuple[int, int, int, int] | None,
                            np.ndarray | None,
                            np.ndarray | None,
                            np.ndarray | None,
                        ],
                    ] = {}
                    for future in as_completed(futures):
                        idx, bbox, warped_roi, score_roi, valid_roi = future.result()
                        batch_results[idx] = (bbox, warped_roi, score_roi, valid_roi)
                        prep_pbar.update(1)
                    prep_elapsed += time.perf_counter() - t0

                    t1 = time.perf_counter()
                    for idx in batch_indices:
                        packed = batch_results.get(idx)
                        if packed is None:
                            blend_pbar.update(1)
                            continue
                        bbox, warped_roi, score_roi, valid_roi = packed
                        if (
                            bbox is None
                            or warped_roi is None
                            or score_roi is None
                            or valid_roi is None
                        ):
                            blend_pbar.update(1)
                            continue

                        y0, y1, x0, x1 = bbox
                        acc_roi = acc[y0:y1, x0:x1]
                        wsum_roi = wsum[y0:y1, x0:x1]
                        coverage_roi = coverage[y0:y1, x0:x1]

                        # Mild per-frame color gain alignment in overlap to reduce "block" perception.
                        overlap = (wsum_roi > 1e-6) & (valid_roi > 0.5) & (score_roi > 1e-4)
                        if np.any(overlap):
                            curr_overlap = acc_roi[overlap] / wsum_roi[overlap, None]
                            ref_mean = curr_overlap.mean(axis=0)
                            src_mean = warped_roi[overlap].mean(axis=0)
                            gain = ref_mean / np.maximum(src_mean, 1e-6)
                            gain = np.clip(gain, 0.88, 1.12)
                            warped_roi *= gain[None, None, :]
                            np.clip(warped_roi, 0.0, 255.0, out=warped_roi)

                        acc_roi += warped_roi * score_roi[:, :, None]
                        wsum_roi += score_roi
                        coverage_roi += valid_roi
                        blend_pbar.update(1)
                    blend_elapsed += time.perf_counter() - t1

    print(f"[time] warp precompute ({workers} threads): {prep_elapsed:.2f}s")
    print(f"[time] blend accumulate: {blend_elapsed:.2f}s")

    pano = (acc / np.maximum(wsum[:, :, None], 1e-6)).clip(0, 255).astype(np.uint8)

    pano = crop_valid_area(pano, coverage)
    print(f"[time] stitch total: {time.perf_counter() - stitch_start:.2f}s")
    return pano, len(accepted)


def main() -> None:
    total_start = time.perf_counter()
    parser = argparse.ArgumentParser(
        description="Extract keyframes from a video segment and stitch a large object panorama."
    )
    parser.add_argument("input_video", help="Input video path.")
    parser.add_argument("output_image", help="Output panorama image path.")
    parser.add_argument("--start", required=True, help="Start time, e.g. 00:47:24.216")
    parser.add_argument("--end", required=True, help="End time, e.g. 00:47:34.310")
    parser.add_argument("--sample-fps", type=float, default=12.0, help="Sampling fps. Default: 12")
    args = parser.parse_args()

    # Quality-oriented defaults (keep these fixed unless you have a special scene):
    # - PREVIEW_WIDTH/STITCH_WIDTH: full-HD level feature matching and output sharpness.
    # - MIN_BLUR/MIN_MOTION_PX: avoid blurry/duplicate frames while keeping camera motion continuity.
    # - FORCE_KEEP_SECONDS: force sparse keep in low-texture regions to avoid missing areas.
    # - FEATHER_RADIUS: larger value softens seams and reduces block-like stitching artifacts.
    # - MAX_OUTPUT_MP: keep high-resolution panorama, but prevent uncontrolled memory growth.
    PREVIEW_WIDTH = 1920
    STITCH_WIDTH = 1920
    MIN_BLUR = 18.0
    MIN_MOTION_PX = 4.0
    FORCE_KEEP_SECONDS = 0.5
    MAX_KEYFRAMES = 260
    FEATHER_RADIUS = 71
    MAX_OUTPUT_MP = 120.0

    if not os.path.isfile(args.input_video):
        raise FileNotFoundError(f"Input video does not exist: {args.input_video}")
    if args.sample_fps <= 0:
        raise ValueError("--sample-fps must be > 0")

    fps = probe_video_fps(args.input_video)
    start_raw = parse_time_to_seconds(args.start)
    end_raw = parse_time_to_seconds(args.end)
    if end_raw <= start_raw:
        raise ValueError("--end must be later than --start")

    start_idx, start_precise = snap_to_frame_time(start_raw, fps)
    end_idx, end_precise = snap_to_frame_time(end_raw, fps)
    if end_idx <= start_idx:
        end_idx = start_idx + 1
        end_precise = end_idx / fps

    print(f"[info] fps={fps:.6f}")
    print(
        f"[info] precise segment: {seconds_to_hhmmss(start_precise)} -> "
        f"{seconds_to_hhmmss(end_precise)} (frame {start_idx} -> {end_idx})"
    )

    extract_start = time.perf_counter()
    keyframes = extract_keyframes(
        video_path=args.input_video,
        start_frame=start_idx,
        end_frame=end_idx,
        video_fps=fps,
        sample_fps=args.sample_fps,
        min_blur=MIN_BLUR,
        min_motion_px=MIN_MOTION_PX,
        force_keep_seconds=FORCE_KEEP_SECONDS,
        preview_width=PREVIEW_WIDTH,
        max_keyframes=MAX_KEYFRAMES,
    )
    print(f"[time] keyframe extraction: {time.perf_counter() - extract_start:.2f}s")
    print(f"[1/2] keyframes selected: {len(keyframes)}")

    stitch_start = time.perf_counter()
    pano, used = stitch_panorama(
        keyframes=keyframes,
        stitch_width=STITCH_WIDTH,
        max_output_megapixels=MAX_OUTPUT_MP,
        feather_radius=FEATHER_RADIUS,
    )
    print(f"[time] stitch pipeline: {time.perf_counter() - stitch_start:.2f}s")
    print(f"[2/2] stitched frames: {used}/{len(keyframes)}")

    write_start = time.perf_counter()
    out_path = Path(args.output_image).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), pano):
        raise RuntimeError(f"Failed to write output image: {out_path}")
    print(f"[time] write image: {time.perf_counter() - write_start:.2f}s")
    print(f"[time] total runtime: {time.perf_counter() - total_start:.2f}s")
    print(f"[done] panorama saved: {out_path}")


if __name__ == "__main__":
    main()
