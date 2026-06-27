"""
Whisper 模型下载脚本
使用清华镜像下载，避免网络问题
"""
import os

# 设置清华镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download

def download_model(model_name="Systran/faster-whisper-medium",
                   local_dir="./models/whisper-medium"):
    print(f"开始下载模型: {model_name}")
    print(f"保存到: {local_dir}")
    print("这可能需要几分钟到几十分钟，请耐心等待...")

    snapshot_download(
        repo_id=model_name,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
    )

    print(f"\n✅ 下载完成！")
    print(f"使用方法：")
    print(f"  export WHISPER_MODEL_PATH=\"{os.path.abspath(local_dir)}\"")
    print(f"  python app.py")


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "Systran/faster-whisper-medium"
    local = sys.argv[2] if len(sys.argv) > 2 else "./models/whisper-medium"
    download_model(model, local)
