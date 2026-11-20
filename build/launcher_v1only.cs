using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

// 一键安装：把内嵌的 payload 解到 %LOCALAPPDATA%\DuskTrainingTool，再运行 install.ps1。
class Installer
{
    const string MARK = "payload/";

    static bool IsTest()
    {
        return !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("DUSK_TEST_ROOT"));
    }

    static void Fail(string msg)
    {
        Console.WriteLine(msg);
        if (!IsTest())
            MessageBox.Show(msg, "安装失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }

    static string PickInstallDir()
    {
        string root = Environment.GetEnvironmentVariable("DUSK_TEST_ROOT");
        if (string.IsNullOrEmpty(root))
            root = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        return Path.Combine(root, "DuskTrainingTool");
    }

    static void Main()
    {
        string dir = PickInstallDir();
        string dirName = Path.GetFileName(dir);
        int count = 0;

        try
        {
            var asm = Assembly.GetExecutingAssembly();
            foreach (var res in asm.GetManifestResourceNames())
            {
                if (!res.StartsWith(MARK)) continue;
                string rel = res.Substring(MARK.Length).Replace('/', Path.DirectorySeparatorChar);
                string target = Path.Combine(dir, rel);
                string parent = Path.GetDirectoryName(target);
                if (!string.IsNullOrEmpty(parent)) Directory.CreateDirectory(parent);
                using (var s = asm.GetManifestResourceStream(res))
                using (var f = File.Create(target))
                    s.CopyTo(f);
                count++;
            }
        }
        catch (Exception e)
        {
            Fail("解压安装文件失败：\n" + e.Message);
            return;
        }

        if (count == 0)
        {
            Fail("安装包损坏（没有内嵌文件）。请重新下载。");
            return;
        }

        string ps1 = Path.Combine(dir, "install.ps1");
        if (!File.Exists(ps1))
        {
            Fail("安装包缺少 install.ps1。请重新下载。");
            return;
        }

        var psi = new ProcessStartInfo("powershell.exe",
            "-NoProfile -ExecutionPolicy Bypass -File \"" + ps1 + "\"" + (IsTest() ? " -Test" : ""));
        psi.WorkingDirectory = dir;
        psi.UseShellExecute = false;
        psi.EnvironmentVariables["DUSK_INSTALL_DIR"] = dir;
        try
        {
            var p = Process.Start(psi);
            p.WaitForExit();
            if (p.ExitCode != 0)
            {
                if (!IsTest())
                    MessageBox.Show("安装没有完成。\n\n请把这张截图发给作者，他会帮你处理。",
                        "训练场换怪 · 安装", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                Environment.Exit(1);
            }
        }
        catch (Exception e)
        {
            Fail("启动安装失败：\n" + e.Message);
        }
    }
}