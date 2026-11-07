// The UI's one seam to the run manager: the local FastAPI server (apiServer.ts), or, in
// the static website build (VITE_PW_TARGET=site), the in-browser engine (apiBrowser.ts).
// Vite inlines the constant, so each build keeps one implementation.

import * as browser from "./apiBrowser";
import * as server from "./apiServer";

export type { Command } from "./apiServer";

const impl: typeof server = import.meta.env.VITE_PW_TARGET === "site" ? browser : server;

export const getStatus = impl.getStatus;
export const listRuns = impl.listRuns;
export const createRun = impl.createRun;
export const deleteRun = impl.deleteRun;
export const fileUrl = impl.fileUrl;
export const downloadName = impl.downloadName;
export const connectRun = impl.connectRun;
export const foldTree = impl.foldTree;
export const downloadRun = impl.downloadRun;
