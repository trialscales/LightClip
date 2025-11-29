
# LightClip v1.2 - 多語系剪貼簿工具（含模板與設定頁）

本專案是 Python 3.13 + PyQt5 的輕量剪貼簿工具，提供：

- 剪貼簿歷史記錄（文字 / 圖片 / 網址 / 檔案）
- 多語系 UI（繁體中文 / English）
- 深色 / 淺色 UI 主題與圖示主題
- 常用模板管理（可設定 1~9 對應 Ctrl+Shift+數字）
- JSON 本機儲存資料
- 系統托盤常駐
- 設定頁（語言 / 主題 / 最大筆數...）
- 關於視窗

## 安裝相依套件

```bash
pip install -r requirements.txt
```

## 執行原始碼

```bash
python main.py
```

## 打包 EXE

```bash
build_exe.bat
```

會產生 `dist/LightClip/LightClip.exe`。

如需安裝程式，請安裝 Inno Setup，使用 `build_installer.iss` 進行打包。
