#!/usr/bin/env python3
"""
Telegodex 配置助手

帮助用户快速生成自定义 Provider 配置
"""

import json
import sys
from pathlib import Path


def print_header():
    """打印欢迎信息"""
    print("""
╔═══════════════════════════════════════════════════════╗
║       Telegodex 自定义 Provider 配置助手             ║
╚═══════════════════════════════════════════════════════╝
""")


def get_input(prompt: str, default: str = "") -> str:
    """获取用户输入"""
    if default:
        prompt = f"{prompt} (默认: {default})"
    value = input(f"{prompt}: ").strip()
    return value if value else default


def create_provider_config():
    """交互式创建 Provider 配置"""
    print_header()
    print("请回答以下问题来创建自定义 Provider 配置：\n")

    # 配置名称
    name = get_input("配置名称（如: ollama, my_api）")
    if not name:
        print("❌ 配置名称不能为空")
        return None

    # Provider 类型（当前只支持 openai_compatible）
    print("\n当前支持的类型: openai_compatible")
    provider_type = "openai_compatible"

    # API Key
    api_key = get_input("API Key（如果不需要可填任意值）")
    if not api_key:
        print("❌ API Key 不能为空")
        return None

    # Base URL
    base_url = get_input("API 基础 URL（例如: http://localhost:11434/v1）")
    if not base_url:
        print("❌ Base URL 不能为空")
        return None

    # 模型列表
    models_input = get_input("可用模型列表（逗号分隔，如: llama3.2,qwen2.5）")
    models = [m.strip() for m in models_input.split(",") if m.strip()] if models_input else []

    # 默认模型
    default_model = ""
    if models:
        default_model = get_input("默认模型", models[0])
    else:
        default_model = get_input("默认模型（如果未指定模型列表，请填写）")

    # 构建配置
    config = {
        name: {
            "type": provider_type,
            "api_key": api_key,
            "base_url": base_url,
        }
    }

    if models:
        config[name]["models"] = models
    if default_model:
        config[name]["default_model"] = default_model

    return config


def show_config_preview(config: dict):
    """显示配置预览"""
    print("\n" + "="*60)
    print("配置预览：")
    print("="*60)
    print(json.dumps(config, indent=2, ensure_ascii=False))
    print("="*60)


def save_config(config: dict, filename: str = "custom_providers.json"):
    """保存配置到文件"""
    filepath = Path(filename)

    # 如果文件已存在，询问是否合并
    if filepath.exists():
        print(f"\n⚠️  配置文件 {filename} 已存在")
        action = get_input("选择操作: [1] 合并配置  [2] 覆盖文件  [3] 另存为", "1")

        if action == "1":
            # 合并配置
            with open(filepath, encoding="utf-8") as f:
                existing_config = json.load(f)
            existing_config.update(config)
            config = existing_config
            print("✓ 将合并到现有配置")

        elif action == "3":
            # 另存为
            new_filename = get_input("新文件名", "custom_providers_new.json")
            filepath = Path(new_filename)

    # 保存文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 配置已保存到: {filepath.absolute()}")
    print("\n下一步：")
    print(f"  1. 检查配置: cat {filepath}")
    print(f"  2. 在 .env 中设置: CUSTOM_PROVIDERS_CONFIG={filepath}")
    print("  3. 重启 Bot: python run.py")


def show_examples():
    """显示配置示例"""
    examples = {
        "Ollama（本地模型）": {
            "ollama": {
                "type": "openai_compatible",
                "api_key": "ollama",
                "base_url": "http://localhost:11434/v1",
                "models": ["llama3.2", "qwen2.5"],
                "default_model": "llama3.2"
            }
        },
        "LiteLLM Proxy": {
            "litellm": {
                "type": "openai_compatible",
                "api_key": "sk-your-key",
                "base_url": "http://localhost:4000",
                "models": ["gpt-4", "claude-3"],
                "default_model": "gpt-4"
            }
        },
        "Azure OpenAI": {
            "azure": {
                "type": "openai_compatible",
                "api_key": "your_azure_key",
                "base_url": "https://your-resource.openai.azure.com/openai/deployments",
                "models": ["gpt-4"],
                "default_model": "gpt-4"
            }
        }
    }

    print("\n常见配置示例：\n")
    for title, example in examples.items():
        print(f"【{title}】")
        print(json.dumps(example, indent=2, ensure_ascii=False))
        print()


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_examples()
        return

    try:
        # 创建配置
        config = create_provider_config()
        if not config:
            return

        # 显示预览
        show_config_preview(config)

        # 确认保存
        confirm = get_input("\n是否保存此配置？[Y/n]", "Y")
        if confirm.lower() in ["y", "yes", ""]:
            save_config(config)
        else:
            print("❌ 已取消保存")

    except KeyboardInterrupt:
        print("\n\n❌ 用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()
