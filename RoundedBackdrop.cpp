// Author: Kerwin
// A compositor-only, click-through companion behind the Qt lyric window.
// The rounded clip applies to the actual host-backdrop visual, not just paint.
#define NOMINMAX
#include <windows.h>
#include <roapi.h>
#include <dwmapi.h>
#include <DispatcherQueue.h>
#include <windows.ui.composition.interop.h>
#include <winrt/Windows.System.h>
#include <winrt/Windows.UI.Composition.h>
#include <winrt/Windows.UI.Composition.Desktop.h>
#include <algorithm>
#include <memory>
using namespace winrt;
using namespace winrt::Windows::UI::Composition;

struct Backdrop {
    HWND window{};
    winrt::Windows::System::DispatcherQueueController queue{nullptr};
    Compositor compositor{nullptr};
    Desktop::DesktopWindowTarget target{nullptr};
    SpriteVisual visual{nullptr};
    CompositionRoundedRectangleGeometry geometry{nullptr};
    Backdrop() {
        HRESULT hr = RoInitialize(RO_INIT_SINGLETHREADED);
        if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) check_hresult(hr);
        if (!winrt::Windows::System::DispatcherQueue::GetForCurrentThread()) {
            DispatcherQueueOptions options{sizeof(DispatcherQueueOptions), DQTYPE_THREAD_CURRENT, DQTAT_COM_NONE};
            check_hresult(CreateDispatcherQueueController(options,
                reinterpret_cast<ABI::Windows::System::IDispatcherQueueController**>(put_abi(queue))));
        }
        WNDCLASSW wc{};
        wc.lpfnWndProc = [](HWND hwnd, UINT message, WPARAM w, LPARAM l) -> LRESULT {
            if (message == WM_NCHITTEST) return HTTRANSPARENT;
            if (message == WM_ERASEBKGND) return 1;
            return DefWindowProcW(hwnd, message, w, l);
        };
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.lpszClassName = L"FloatingLyricsRoundedBackdrop";
        RegisterClassW(&wc);
        window = CreateWindowExW(WS_EX_NOREDIRECTIONBITMAP | WS_EX_TOOLWINDOW |
            WS_EX_NOACTIVATE | WS_EX_TRANSPARENT, wc.lpszClassName, L"", WS_POPUP,
            0, 0, 1, 1, nullptr, nullptr, wc.hInstance, nullptr);
        if (!window) throw_last_error();
        BOOL enabled = TRUE;
        check_hresult(DwmSetWindowAttribute(window, DWMWA_USE_HOSTBACKDROPBRUSH, &enabled, sizeof(enabled)));
        compositor = Compositor();
        auto interop = compositor.as<ABI::Windows::UI::Composition::Desktop::ICompositorDesktopInterop>();
        check_hresult(interop->CreateDesktopWindowTarget(window, false,
            reinterpret_cast<ABI::Windows::UI::Composition::Desktop::IDesktopWindowTarget**>(put_abi(target))));
        geometry = compositor.CreateRoundedRectangleGeometry();
        visual = compositor.CreateSpriteVisual();
        visual.Brush(compositor.CreateHostBackdropBrush());
        visual.Clip(compositor.CreateGeometricClip(geometry));
        target.Root(visual);
    }
    ~Backdrop() {
        if (target) target.Root(nullptr);
        if (window) DestroyWindow(window);
    }
};
static std::unique_ptr<Backdrop> backdrop;

extern "C" __declspec(dllexport) HRESULT __cdecl fl_blur_update(HWND owner,
    int x, int y, int width, int height, int radius, int topmost, int visible) noexcept {
    try {
        if (!visible) {
            if (backdrop) ShowWindow(backdrop->window, SW_HIDE);
            return S_OK;
        }
        if (!backdrop) backdrop = std::make_unique<Backdrop>();
        RECT ownerRect{};
        if (GetWindowRect(owner, &ownerRect)) {
            x = ownerRect.left;
            y = ownerRect.top;
            width = ownerRect.right - ownerRect.left;
            height = ownerRect.bottom - ownerRect.top;
        }
        radius = std::clamp(radius, 0, std::min(width, height) / 2);
        backdrop->visual.Size({float(width), float(height)});
        backdrop->geometry.Size({float(width), float(height)});
        backdrop->geometry.CornerRadius({float(radius), float(radius)});
        SetWindowPos(backdrop->window, topmost ? HWND_TOPMOST : HWND_NOTOPMOST,
            x, y, width, height, SWP_NOACTIVATE);
        SetWindowPos(backdrop->window, owner, x, y, width, height, SWP_NOACTIVATE | SWP_SHOWWINDOW);
        return S_OK;
    } catch (...) {
        if (backdrop) ShowWindow(backdrop->window, SW_HIDE);
        return to_hresult();
    }
}

extern "C" __declspec(dllexport) void __cdecl fl_blur_close() noexcept {
    backdrop.reset();
}
