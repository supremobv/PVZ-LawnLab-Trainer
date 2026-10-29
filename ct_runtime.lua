-- Embedded opt-in adapter. Merely opening the table makes no game changes.
if _G.LawnLabCE and _G.LawnLabCE.version~='5.14' then
  pcall(function()if _G.LawnLabCE.folder then _G.LawnLabCE.command('STOP')end end)
  if _G.LawnLabCE.timer then _G.LawnLabCE.timer.destroy()end
  _G.LawnLabCE=nil
end
if not _G.LawnLabCE then
  local R={version='5.14',serial=0,busy=false,records={}}
  _G.LawnLabCE=R
  local function read(path)
    local f=io.open(path,'rb');if not f then return nil end
    local s=f:read('*a');f:close();return s
  end
  local function write(path,text)
    local f=assert(io.open(path,'wb'),'Cannot write CT session file');f:write(text);f:close()
  end
  local function waitFile(path,ms)
    local untilTick=getTickCount()+ms
    repeat
      local text=read(path);if text then return text end
      sleep(30);processMessagesPaintOnly()
    until getTickCount()>untilTick
    error('LawnLab CT helper did not respond. Reopen the controller after checking its status.')
  end
  function R.start()
    if R.folder and read(R.folder..'stopped')then
      R.folder=nil
      if R.timer then R.timer.destroy();R.timer=nil end
    end
    if R.folder then
      assert(getOpenedProcessID()==R.pid,'CE process changed. Stop this CT session before switching games.')
      return
    end
    R.pid=getOpenedProcessID();assert(R.pid and R.pid>0,'Select the supported PVZ process in CE first.')
    local dialog=createOpenDialog(nil)
    dialog.Title='Select the matching LawnLab 5.14 executable'
    dialog.Filter='LawnLab.exe|LawnLab.exe'
    local chosen=dialog.execute();local exe=dialog.FileName;dialog.destroy()
    assert(chosen,'No LawnLab executable selected.')
    local token=string.format('%08x%08x%08x%08x',getCheatEngineProcessID(),os.time(),math.random(0,0x7fffffff),math.random(0,0x7fffffff))
    local folder=assert(os.getenv('LOCALAPPDATA'))..'\\LawnLab\\ce\\'..token..'\\'
    shellExecute(exe,'--ct-bridge '..token..' '..tostring(R.pid),extractFilePath(exe),0)
    local ready=waitFile(folder..'ready',20000)
    assert(ready=='OK|5.14','Matching LawnLab 5.14 required. Helper response: '..ready)
    R.folder=folder
    R.timer=createTimer(nil,false);R.timer.Interval=1000
    R.timer.OnTimer=function()
      if R.busy then return end
      local root=getAddressList().getMemoryRecordByID(1)
      if getOpenedProcessID()~=R.pid or not root or root.Description~='LawnLab 5.14 — verified CT controller' then
        pcall(function()R.command('STOP')end);R.timer.destroy();R.timer=nil;return
      end
      if read(folder..'stopped')then
        R.timer.destroy();R.timer=nil
        showMessage('LawnLab CT helper stopped. Controls were reset where possible. Check the local cleanup-error file if cleanup failed.')
        return
      end
      write(folder..'heartbeat','alive')
    end
    R.timer.Enabled=true
  end
  function R.command(command)
    assert(not R.busy,'A CT operation is already running.')
    R.start();R.busy=true
    local ok,result=pcall(function()
      R.serial=R.serial+1;local id=tostring(R.serial)
      write(R.folder..'heartbeat','alive');os.remove(R.folder..'response')
      write(R.folder..'request.tmp',id..'|'..command)
      assert(os.rename(R.folder..'request.tmp',R.folder..'request'))
      local reply=waitFile(R.folder..'response',12000)
      local status,replyID,states,message=reply:match('^(%u+)|(%d+)\n([^\n]*)\n(.*)$')
      assert(replyID==id,'CT response sequence mismatch.')
      local enabled={};for name in (states or ''):gmatch('[^,]+')do enabled[name]=true end
      R.syncing=true
      for name,recordID in pairs(R.records)do
        local record=getAddressList().getMemoryRecordByID(recordID)
        -- Only uncheck modes disabled by conflict resolution; never auto-enable anything.
        if record and record.Active and not enabled[name]then record.Active=false end
      end
      R.syncing=false
      assert(status=='OK',message or 'CT operation failed.')
      if command=='STOP'and R.timer then R.timer.destroy();R.timer=nil end
      return true
    end)
    R.busy=false;R.syncing=false
    if not ok then error(result)end
    return result
  end
end

