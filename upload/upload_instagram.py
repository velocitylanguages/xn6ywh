import os
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def upload_to_instagram(video_path, caption, is_story=False):
    media_type = 'STORIES' if is_story else 'REELS'

    print("\n" + "=" * 60)
    print(f"INSTAGRAM {media_type} UPLOAD STARTING")
    print("=" * 60)

    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
    ig_user_id = os.getenv('INSTAGRAM_ACCOUNT_ID') or os.getenv('IG_USER_ID')
    fb_page_id = os.getenv('FACEBOOK_PAGE_ID')

    def mask(s): return f"{s[:10]}...{s[-4:]}" if s and len(s) > 10 else ("PLACEHOLDER" if s == "***" else "MISSING")
    print(f"[instagram] IG User ID: {ig_user_id}")
    print(f"[instagram] FB Page ID: {fb_page_id}")
    print(f"[instagram] Token: {mask(access_token)}")

    if not access_token or not ig_user_id:
        return {'status': 'skipped', 'reason': 'Missing credentials', 'platform': 'instagram'}

    # Auto-detect IG Business Account ID for EAAM tokens (fallback if env var is wrong)
    if access_token.startswith('EAAM'):
        try:
            me = requests.get(f"https://graph.facebook.com/v21.0/me?fields=id,name&access_token={access_token}", timeout=10)
            if me.status_code == 200:
                detected_page_id = me.json().get('id')
                if not fb_page_id:
                    fb_page_id = detected_page_id
                ig = requests.get(f"https://graph.facebook.com/v21.0/{detected_page_id}?fields=instagram_business_account&access_token={access_token}", timeout=10)
                if ig.status_code == 200:
                    acct = ig.json().get('instagram_business_account')
                    if acct and acct.get('id'):
                        detected_ig_id = acct.get('id')
                        if detected_ig_id != ig_user_id:
                            print(f"[instagram] Using detected IG Business Account: {detected_ig_id}")
                            ig_user_id = detected_ig_id
        except Exception as e:
            print(f"[instagram] EAAM detection error: {e}")

    print("[instagram] Credentials loaded")

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_size_mb = video_path_obj.stat().st_size / (1024 * 1024)
    print(f"[instagram] Video: {video_path} ({file_size_mb:.2f} MB)")

    caption_limited = caption[:2200] if len(caption) > 2200 else caption
    print(f"[instagram] Caption: {len(caption_limited)} chars")

    try:
        video_url = None

        if access_token.startswith('IGAA'):
            print("[instagram] IGAA token - using tmpfiles.org upload")
            with open(video_path_obj, 'rb') as f:
                tr = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': ('video.mp4', f, 'video/mp4')}, timeout=180)
            if tr.status_code != 200:
                raise Exception(f"tmpfiles failed: {tr.status_code}")
            td = tr.json()
            if td.get('status') != 'success':
                raise Exception(f"tmpfiles error: {td}")
            tu = td.get('data', {}).get('url', '')
            video_url = tu.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
            print(f"[instagram] tmpfiles URL: {video_url}")
        else:
            print("[instagram] EAAM token - uploading via Facebook video_reels API")
            page_id_for_upload = fb_page_id or ig_user_id
            print(f"[instagram] Using page_id={page_id_for_upload} for upload")

            file_size = video_path_obj.stat().st_size

            print("[instagram] Start upload session...")
            start_url = f"https://graph.facebook.com/v21.0/{page_id_for_upload}/video_reels"
            sr = requests.post(start_url, data={'access_token': access_token, 'upload_phase': 'start', 'file_size': file_size}, timeout=30)
            if sr.status_code != 200:
                raise Exception(f"FB start failed: {sr.text}")
            sj = sr.json()
            video_id = sj.get('video_id')
            upload_url = sj.get('upload_url')
            if not video_id:
                raise Exception(f"No video_id: {sj}")
            print(f"[instagram] video_id={video_id}")

            print("[instagram] Transferring video...")
            with open(video_path, 'rb') as f:
                tr2 = requests.post(upload_url, headers={'Authorization': f'OAuth {access_token}', 'offset': '0', 'file_size': str(file_size)}, data=f, timeout=600)
            if tr2.status_code != 200:
                raise Exception(f"FB transfer failed: {tr2.text}")

            print("[instagram] Finalizing upload...")
            fr = requests.post(start_url, data={'access_token': access_token, 'upload_phase': 'finish', 'video_id': video_id, 'video_state': 'DRAFT'}, timeout=60)
            if fr.status_code != 200:
                raise Exception(f"FB finish failed: {fr.text}")

            print("[instagram] Fetching CDN URL...")
            vr = requests.get(f"https://graph.facebook.com/v21.0/{video_id}", params={'fields': 'source', 'access_token': access_token}, timeout=30)
            if vr.status_code == 200:
                video_url = vr.json().get('source')
            if not video_url:
                video_url = f"https://graph.facebook.com/v21.0/{video_id}?access_token={access_token}"
                print("[instagram] Using fallback video URL")
            else:
                print(f"[instagram] Facebook CDN URL")

        print(f"[instagram] Creating {media_type} container...")
        container_params = {'media_type': media_type, 'video_url': video_url, 'access_token': access_token}
        if not is_story:
            container_params['caption'] = caption_limited

        cr = requests.post(f"https://graph.facebook.com/v21.0/{ig_user_id}/media", params=container_params, timeout=60)
        if cr.status_code != 200:
            raise Exception(f"Container failed: {cr.json().get('error', {}).get('message', 'Unknown')}")

        container_id = cr.json().get('id')
        print(f"[instagram] Container: {container_id}")

        print("[instagram] Processing...")
        max_wait = 180
        waited = 0
        while waited < max_wait:
            sr2 = requests.get(f"https://graph.facebook.com/v21.0/{container_id}", params={'fields': 'status_code,status', 'access_token': access_token}, timeout=30)
            sd = sr2.json()
            sc = sd.get('status_code') or sd.get('status', 'UNKNOWN')
            print(f"[instagram] Status: {sc} (waited {waited}s)")
            if sc == 'FINISHED':
                print("[instagram] Processing complete!")
                break
            elif sc == 'ERROR':
                raise Exception(sd.get('error_message', 'Video processing failed'))
            time.sleep(15)
            waited += 15

        if waited >= max_wait:
            print("[instagram] Timed out, attempting publish anyway...")

        time.sleep(2)
        print("[instagram] Publishing...")
        max_retries = 3
        pr = None
        for attempt in range(max_retries):
            pr = requests.post(f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish", params={'creation_id': container_id, 'access_token': access_token}, timeout=60)
            if pr.status_code == 200:
                break
            print(f"[instagram] Publish attempt {attempt+1} failed, retrying...")
            time.sleep(10)

        if not pr or pr.status_code != 200:
            raise Exception(f"Publish failed: {pr.json().get('error', {}).get('message', 'Unknown') if pr else 'No response'}")

        media_id = pr.json().get('id')
        print(f"[instagram] SUCCESS! Media ID: {media_id}")
        return {'id': media_id, 'platform': 'instagram', 'status': 'success'}

    except Exception as e:
        print(f"[instagram] Error: {e}")
        raise


if __name__ == '__main__':
    vf = Path('test.mp4')
    if vf.exists():
        try:
            r = upload_to_instagram(str(vf), "Test")
            print(f"Result: {r}")
        except Exception as e:
            print(f"Failed: {e}")
    else:
        print("Video not found")