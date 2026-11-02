// Author: Kerwin
// Read-only Windows media sessions and process presence for four players.
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <roapi.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Media.Control.h>
#include <winrt/Windows.Data.Json.h>
#include <iostream>
#include <map>
#include <chrono>
#include <algorithm>
using namespace winrt;
using namespace winrt::Windows::Media::Control;
using namespace winrt::Windows::Data::Json;
static void str(JsonObject& row, wchar_t const* key, hstring value) {row.Insert(key,JsonValue::CreateStringValue(value));}
static void num(JsonObject& row, wchar_t const* key, double value) {row.Insert(key,JsonValue::CreateNumberValue(value));}
static void flag(JsonObject& row, wchar_t const* key, bool value) {row.Insert(key,JsonValue::CreateBooleanValue(value));}
static std::wstring lower(std::wstring value) {std::transform(value.begin(),value.end(),value.begin(),towlower);return value;}
static std::wstring player(std::wstring value) {
    value=lower(value);
    if(value.find(L"kugou")!=std::wstring::npos)return L"kugou";
    if(value.find(L"qqmusic")!=std::wstring::npos)return L"qq";
    if(value.find(L"cloudmusic")!=std::wstring::npos)return L"netease";
    if(value.find(L"sodamusic")!=std::wstring::npos || value.find(L"汽水")!=std::wstring::npos)return L"soda";
    return L"";
}
int main(int argc,char** argv) {
    init_apartment(apartment_type::multi_threaded);
    auto manager=GlobalSystemMediaTransportControlsSessionManager::RequestAsync().get();
    bool once=argc>1 && std::string(argv[1])=="--once";
    do {
        try {
            std::map<std::wstring,bool> running;
            HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
            PROCESSENTRY32W entry{sizeof(entry)};
            if(Process32FirstW(snapshot,&entry)) do {
                auto name=lower(entry.szExeFile);
                if(name==L"kugou.exe" || name==L"qqmusic.exe" || name==L"cloudmusic.exe" || name==L"sodamusic.exe") {
                    auto id=player(name);if(!id.empty())running[id]=true;
                }
            }while(Process32NextW(snapshot,&entry));
            CloseHandle(snapshot);
            JsonObject players;
            for(auto id:{L"kugou",L"qq",L"netease",L"soda"}) {JsonObject row;flag(row,L"running",running[id]);flag(row,L"ok",false);players.Insert(id,row);}
            for(auto session:manager.GetSessions()) {
                auto id=player(std::wstring(session.SourceAppUserModelId()));if(id.empty() || !running[id])continue;
                try {
                    auto media=session.TryGetMediaPropertiesAsync().get();
                    auto info=session.GetPlaybackInfo();auto timeline=session.GetTimelineProperties();
                    auto status=info.PlaybackStatus();
                    double position=std::chrono::duration<double,std::milli>(timeline.Position()).count();
                    double duration=std::chrono::duration<double,std::milli>(timeline.EndTime()).count();
                    double lag=std::chrono::duration<double,std::milli>(clock::now()-timeline.LastUpdatedTime()).count();
                    bool valid=timeline.LastUpdatedTime().time_since_epoch().count()>0 && duration>0;
                    if(valid && status==GlobalSystemMediaTransportControlsSessionPlaybackStatus::Playing) {
                        // A play/pause transition can briefly retain a very old
                        // timeline timestamp. Never extrapolate it to song end.
                        if(id!=L"soda" && lag>=0 && lag<3000)position+=lag;
                    }
                    JsonObject row;flag(row,L"running",true);flag(row,L"ok",!media.Title().empty());
                    str(row,L"title",media.Title());str(row,L"artist",media.Artist());str(row,L"album",media.AlbumTitle());
                    str(row,L"identity",hstring(std::wstring(media.Artist())+L" - "+std::wstring(media.Title())));
                    str(row,L"state",status==GlobalSystemMediaTransportControlsSessionPlaybackStatus::Playing?L"playing":L"paused");
                    str(row,L"source",L"SMTC");str(row,L"precision",L"timeline");flag(row,L"timeline_valid",valid);
                    num(row,L"position_ms",std::min(position,duration>0?duration:position));num(row,L"duration_ms",duration);
                    if(id==L"soda") {
                        num(row,L"timeline_updated_ms",std::chrono::duration<double,std::milli>(timeline.LastUpdatedTime().time_since_epoch()).count());
                        num(row,L"timeline_age_ms",lag);
                    }
                    players.Insert(id,row);
                }catch(...){}
            }
            JsonObject root;root.Insert(L"players",players);
            std::cout<<to_string(root.Stringify())<<std::endl;
        }catch(...){std::cout<<"{\"players\":{}}"<<std::endl;}
        if(!once)Sleep(250);
    }while(!once);
}
