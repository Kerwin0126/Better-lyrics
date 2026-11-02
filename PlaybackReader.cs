// Author: Kerwin
// Read-only KuGou adapter. Its Qt UIA bridge stalls; use native MSAA instead.
using System;
using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using Accessibility;

class PlaybackReader {
    [ComImport, Guid("35855B5B-C566-4FD0-A7B1-E65465600394"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAccessibleValue {
        [PreserveSig] int GetCurrentValue([MarshalAs(UnmanagedType.Struct)] out object value);
        [PreserveSig] int SetCurrentValue([MarshalAs(UnmanagedType.Struct)] object value);
        [PreserveSig] int GetMaximumValue([MarshalAs(UnmanagedType.Struct)] out object value);
        [PreserveSig] int GetMinimumValue([MarshalAs(UnmanagedType.Struct)] out object value);
    }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int maxCount);
    [DllImport("user32.dll")]
    static extern bool IsWindow(IntPtr hwnd);
    delegate bool WindowVisitor(IntPtr hwnd,IntPtr parameter);
    [DllImport("user32.dll")]
    static extern bool EnumWindows(WindowVisitor visitor,IntPtr parameter);
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint processId);
    [DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr hwnd);
    static IntPtr knownWindow;
    static string Title(IntPtr hwnd) {var text=new StringBuilder(1024); GetWindowText(hwnd,text,text.Capacity); return text.ToString();}
    [DllImport("oleacc.dll")]
    static extern int AccessibleObjectFromWindow(IntPtr hwnd, uint objectId, ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out object result);
    [DllImport("oleacc.dll")]
    static extern int AccessibleChildren(IAccessible parent, int start, int count, [Out,MarshalAs(UnmanagedType.LPArray,SizeParamIndex=2)] object[] children, out int obtained);
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
    static readonly Regex Clock = new Regex(@"^(\d+):(\d{2})/(\d+):(\d{2})$");
    static bool trace;
    static string cachedTitle;
    static Node cachedTime, cachedButton;
    static IAccessibleValue preciseValue;
    static bool netease;
    static Node netProgress, netButton;
    static string netDiagnostic="";
    static string netWindowTitle="",netState="unknown";
    static DateTime netRefreshed=DateTime.MinValue;
    static IntPtr FindNetEaseWindow() {
        // Renderer/helper processes also own untitled top-level windows.
        // Process.MainWindowHandle can pick one of those instead of the player.
        var owners=new HashSet<uint>();
        foreach(var process in Process.GetProcessesByName("cloudmusic"))owners.Add((uint)process.Id);
        IntPtr found=IntPtr.Zero;
        EnumWindows(delegate(IntPtr hwnd,IntPtr unused) {
            uint owner;GetWindowThreadProcessId(hwnd,out owner);
            if(!owners.Contains(owner) || !IsWindowVisible(hwnd))return true;
            string caption=Title(hwnd);
            if(caption.Contains(" - ") || caption.Contains("网易云音乐")) {
                found=hwnd;return false;
            }
            return true;
        },IntPtr.Zero);
        return found;
    }
    static Dictionary<string,object> ReadNetEase() {
        IntPtr hwnd=FindNetEaseWindow();
        if(hwnd==IntPtr.Zero){netWindowTitle="";throw new Exception("网易云音乐未打开");}
        string title=Title(hwnd);
        netWindowTitle=title;
        if(knownWindow!=hwnd || cachedTitle!=title || netProgress==null || netButton==null || (DateTime.UtcNow-netRefreshed).TotalSeconds>2) {
            knownWindow=hwnd;netProgress=null;netButton=null;
            var iid=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");object root;
            Marshal.ThrowExceptionForHR(AccessibleObjectFromWindow(hwnd,0xfffffffc,ref iid,out root));
            var queue=new Queue<IAccessible>();queue.Enqueue((IAccessible)root);int visited=0;
            while(queue.Count>0 && visited++<3000 && (netProgress==null || netButton==null)) {
                var parent=queue.Dequeue();var children=Children(parent);
                bool controls=children.Exists(n=>n.Name=="pre") && children.Exists(n=>n.Name=="next");
                foreach(var node in children) {
                    if(node.Name=="播放进度调节" && (node.State&0x18000)==0)netProgress=node;
                    if(controls && (node.Name=="play" || node.Name=="pause") && (node.State&0x18000)==0)netButton=node;
                    var child=node.Container;if(child!=null)queue.Enqueue(child);
                }
            }
            netDiagnostic="nodes="+visited+",progress="+(netProgress!=null)+",button="+(netButton!=null)+",hwnd="+hwnd+",title="+title;
            cachedTitle=title;
            netRefreshed=DateTime.UtcNow;
        }
        if(netProgress==null || netButton==null)throw new Exception("请展开网易云主窗口，以读取播放进度");
        int x,y,w,h;netProgress.Owner.accLocation(out x,out y,out w,out h,netProgress.Id);
        if(w<=0)throw new Exception("网易云播放进度条不可见");
        var bounds=new List<int[]>();
        foreach(var node in Children(netProgress.Container)) {
            int cx,cy,cw,ch;node.Owner.accLocation(out cx,out cy,out cw,out ch,node.Id);
            bounds.Add(new int[]{cx,cy,cw,ch});
        }
        double fraction=ProgressFraction(bounds,x,y,w,h);
        var row=new Dictionary<string,object>();row["ok"]=true;row["progress_fraction"]=fraction;
        netState=netButton.Name=="pause"?"playing":"paused";
        row["state"]=netState;row["window_title"]=title;
        row["source"]="MSAA progress geometry";row["precision"]="fraction";
        row["sampled_unix_ms"]=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();return row;
    }
    static double ProgressFraction(List<int[]> children,int x,int y,int w,int h) {
        // The home minibar contains a full-width rail BEFORE the filled segment.
        // The detail view omits that rail. Taking the first rectangle reported 100%
        // throughout home-page playback. The shorter co-located strip is the fill.
        int fill=w;bool found=false,empty=false;
        foreach(var b in children) {
            if(b[2]==0 && b[3]==0){empty=true;continue;}
            if(Math.Abs(b[0]-x)<=1 && Math.Abs(b[1]-y)<=1 && b[3]==h && b[2]>=0 && b[2]<=w) {
                fill=Math.Min(fill,b[2]);found=true;
            }
        }
        if(empty && (!found || fill==w))return 0;
        if(!found || w<=0)throw new Exception("网易云进度条结构已变化");
        return (double)fill/w;
    }
    class Node {
        public IAccessible Owner; public object Id;
        public Node(IAccessible owner, object id) {Owner=owner; Id=id;}
        public string Name {get {return Owner.get_accName(Id) ?? "";}}
        public string Value {get {return Owner.get_accValue(Id) ?? "";}}
        public int Role {get {return Convert.ToInt32(Owner.get_accRole(Id));}}
        public int State {get {return Convert.ToInt32(Owner.get_accState(Id));}}
        public IAccessible Container {get {return Id is int && (int)Id==0 ? Owner : Owner.get_accChild(Id) as IAccessible;}}
    }
    static List<Node> Children(IAccessible parent) {
        var result=new List<Node>();
        int count=Math.Min(parent.accChildCount,4096);
        if(count==0) return result;
        object[] items=new object[count]; int obtained;
        Marshal.ThrowExceptionForHR(AccessibleChildren(parent,0,count,items,out obtained));
        for(int i=0;i<obtained;i++) {
            var accessible=items[i] as IAccessible;
            if(accessible!=null) result.Add(new Node(accessible,0));
            else if(items[i] is int) result.Add(new Node(parent,items[i]));
        }
        return result;
    }
    static bool CanDescend(int role) {
        return role!=0x21 && role!=0x22 && role!=0x24 && role!=0x3c && role!=0x2b && role!=0x29 && role!=0x2a && role!=0x33;
    }
    static double Seconds(Match m,int group) {return int.Parse(m.Groups[group].Value)*60+int.Parse(m.Groups[group+1].Value);}
    static Dictionary<string,object> Read() {
        if(knownWindow==IntPtr.Zero || !IsWindow(knownWindow) || !Title(knownWindow).Contains("酷狗音乐")) {
            knownWindow=IntPtr.Zero;
            foreach(var p in Process.GetProcessesByName("KuGou")) {
                if(p.MainWindowHandle!=IntPtr.Zero && p.MainWindowTitle.Contains("酷狗音乐")) {knownWindow=p.MainWindowHandle; break;}
            }
        }
        if(knownWindow==IntPtr.Zero) throw new Exception("未找到酷狗主窗口");
        string title=Title(knownWindow);
        if(cachedTitle!=title || cachedTime==null || cachedButton==null) {
        var iid=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71"); object root;
        Marshal.ThrowExceptionForHR(AccessibleObjectFromWindow(knownWindow,0xfffffffc,ref iid,out root));
        var queue=new Queue<IAccessible>(); queue.Enqueue((IAccessible)root);
        IAccessible panel=null; Node slider=null;
        int visited=0;
        while(queue.Count>0 && visited++<150 && slider==null) {
            var parent=queue.Dequeue();
            var children=Children(parent);
            foreach(var node in children) {
                if(node.Name=="进度") {slider=node; panel=parent; break;}
            }
            if(slider==null) foreach(var node in children) {
                if(CanDescend(node.Role)) {var child=node.Container; if(child!=null) queue.Enqueue(child);}
            }
        }
        if(slider==null) throw new Exception("酷狗未提供进度控件，请展开主窗口");
        try { preciseValue=slider.Owner as IAccessibleValue; } catch { preciseValue=null; }
        string timeText=null;
        queue.Clear(); queue.Enqueue(panel); visited=0;
        while(queue.Count>0 && visited++<80) {
            foreach(var node in Children(queue.Dequeue())) {
                string name=node.Name;
                int role=node.Role;
                if(Clock.IsMatch(name)) {timeText=name; cachedTime=node;}
                if(role==0x2b && (name=="暂停" || name=="播放")) cachedButton=node;
                if(CanDescend(role)) {var child=node.Container; if(child!=null) queue.Enqueue(child);}
            }
        }
        if(timeText==null) throw new Exception("未找到播放时间文字");
        cachedTitle=title;
        }
        string timeTextNow=cachedTime.Name;
        string buttonName=cachedButton.Name;
        var match=Clock.Match(timeTextNow);
        if(!match.Success) throw new Exception("播放控件已刷新，重新连接");
        double seconds=Seconds(match,1), duration=Seconds(match,3);
        string precision="second";
        if(preciseValue!=null) {
            try {
                object raw;
                if(preciseValue.GetCurrentValue(out raw)==0) {
                    double precise=Convert.ToDouble(raw)/100.0;
                    if(Math.Abs(precise-seconds)<1.5) {seconds=precise; precision="centisecond";}
                }
            } catch { preciseValue=null; }
        }
        if(Title(knownWindow)!=title) throw new Exception("正在切歌，等待稳定");
        var row=new Dictionary<string,object>();
        row["ok"]=true;
        row["identity"]=Regex.Replace(title,@"\s*-\s*酷狗音乐\s*$", "").Trim();
        row["position_ms"]=(long)Math.Round(seconds*1000); row["duration_ms"]=(long)(duration*1000);
        row["state"]=buttonName=="暂停"?"playing":buttonName=="播放"?"paused":"unknown";
        row["precision"]=precision; row["source"]="MSAA";
        row["sampled_unix_ms"]=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        if(trace) Console.Error.WriteLine("read " + row["position_ms"]);
        return row;
    }
    [MTAThread]
    static void Main(string[] args) {
        Console.OutputEncoding=new UTF8Encoding(false);
        if(Array.IndexOf(args,"--test-progress")>=0) {
            int[][][] cases={
                new int[][]{new int[]{0,-10,1000,23},new int[]{0,0,1000,3},new int[]{0,0,460,3},new int[]{460,0,4,3}},
                new int[][]{new int[]{0,-10,1000,23},new int[]{0,0,460,3},new int[]{460,0,4,3}},
                new int[][]{new int[]{0,0,1000,3},new int[]{0,0,0,0}},
                new int[][]{new int[]{0,0,1000,3},new int[]{0,0,1000,3}}
            };
            double[] expected={.46,.46,0,1};
            for(int i=0;i<cases.Length;i++)if(Math.Abs(ProgressFraction(new List<int[]>(cases[i]),0,0,1000,3)-expected[i])>.0001)throw new Exception("progress regression "+i);
            Console.WriteLine("Home/detail/zero/end progress checks passed");return;
        }
        foreach(var arg in args) if(arg.StartsWith("--dump=")) {
            Process process=null;foreach(var candidate in Process.GetProcessesByName(arg.Substring(7))) if(candidate.MainWindowHandle!=IntPtr.Zero){process=candidate;break;}
            if(process==null)return;
            var iid=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71"); object root;
            Marshal.ThrowExceptionForHR(AccessibleObjectFromWindow(process.MainWindowHandle,0xfffffffc,ref iid,out root));
            var queue=new Queue<IAccessible>(); queue.Enqueue((IAccessible)root); int visited=0;
            while(queue.Count>0 && visited++<3000) foreach(var node in Children(queue.Dequeue())) {
                try {
                    if(node.Name=="播放进度调节") {
                        int x,y,w,h;node.Owner.accLocation(out x,out y,out w,out h,node.Id);
                        Console.Error.WriteLine("PROGRESS state="+node.State+" "+x+","+y+","+w+","+h);
                        var inner=node.Container;
                        if(inner!=null)foreach(var c in Children(inner)) {
                            c.Owner.accLocation(out x,out y,out w,out h,c.Id);Console.Error.WriteLine("CHILD "+c.Name+" state="+c.State+" "+x+","+y+","+w+","+h);
                            var inner2=c.Container;if(inner2!=null)foreach(var c2 in Children(inner2)){c2.Owner.accLocation(out x,out y,out w,out h,c2.Id);Console.Error.WriteLine("GRANDCHILD "+c2.Name+" "+x+","+y+","+w+","+h);}
                        }
                    }
                    Console.WriteLine(Json.Serialize(new {name=node.Name,value=node.Value,role=node.Role,state=node.State})); var child=node.Container;if(child!=null)queue.Enqueue(child);
                }catch{}
            }
            return;
        }
        bool once=Array.IndexOf(args,"--once")>=0;
        trace=Array.IndexOf(args,"--trace")>=0;
        netease=Array.IndexOf(args,"--netease")>=0;
        int consecutiveErrors=0;
        do {
            object row;
            try {row=netease?ReadNetEase():Read();consecutiveErrors=0;}
            catch(Exception e) {consecutiveErrors++;cachedTime=null; cachedButton=null;netProgress=null;netButton=null; row=new {ok=false,error=e.Message,reader_detail=netDiagnostic,window_title=netease?netWindowTitle:"",state=netState,sampled_unix_ms=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()};}
            try {Console.WriteLine(Json.Serialize(row)); Console.Out.Flush();} catch {break;}
            if(once) break;
            // Bound recovery from unavailable accessibility objects. The host
            // recreates this reader without touching the music player itself.
            if(netease && consecutiveErrors>=5)break;
            Thread.Sleep(100);
        } while(true);
    }
}
