import type {IndexName} from './index-names.js';
export type {IndexName} from './index-names.js';
export type BBox = [number,number,number,number];
export type BandValue = number | number[];
export interface Asset {href:string;type?:string;title?:string;roles?:string[]}
export interface Scene {type:'Feature';id:string;collection?:string;geometry:unknown;properties:Record<string,unknown>;assets:Record<string,Asset>}
export interface Manifest {type:'FeatureCollection';features:Scene[];universal_satellite?:Record<string,unknown>}
export interface SearchOptions {dataset:string;bbox:BBox;start:string;end:string;cloud?:number;limit?:number}
export interface DownloadOptions {manifest_path:string;asset_keys:string[];output_dir:string;sign_planetary?:boolean;overwrite?:boolean;workers?:number;resume?:boolean;retries?:number}
export interface DownloadResult {downloaded:string[];failed:{scene:string;asset:string;error:string}[];cancelled:boolean}
export interface ProfileOptions {latitude:number;longitude:number;model?:'ecmwf_ifs'|'gfs_seamless';depth?:string;variables?:string[]}
export interface IndexDefinition {short_name:string;long_name:string;formula:string;bands:string[];reference:string;platforms:string[];application_domain:string}
export const indices: Record<IndexName,IndexDefinition>;
export const constants: Record<string,{default:number|null;description:string;short_name:string}>;
export function computeIndex(name:IndexName,bands:Record<string,number>,constants?:Record<string,number>):number;
export function computeIndex(name:IndexName,bands:Record<string,number[]>,constants?:Record<string,number>):number[];
/** Native spectral math; geospatial/network methods use the installed Python core. */
export class Client {
 constructor(options?:{python?:string;signal?:AbortSignal});
 sources(options?:{category?:string}):Promise<Record<string,unknown>[]>;
 search(options:SearchOptions):Promise<Manifest>;
 environment(kind:'forecast'|'air-quality'|'soil',options:ProfileOptions):Promise<Record<string,unknown>>;
 weather(options:{latitude:number;longitude:number;start:string;end:string;variables?:string[]}):Promise<Record<string,unknown>>;
 download(options:DownloadOptions):Promise<DownloadResult>;
 summary(manifest:string):Promise<Record<string,unknown>>;
 rasterIndex(name:IndexName,output:string,bands:Record<string,string>,constants?:Record<string,number>):Promise<string>;
 crop(options:{source:string;boundary:string;output:string;max_pixels?:number}):Promise<string>;
 toa(options:{input_path:string;mtl_path:string;band:number;output:string}):Promise<string>;
 computeIndex:typeof computeIndex;
}
