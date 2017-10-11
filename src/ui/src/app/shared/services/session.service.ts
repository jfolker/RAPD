import { Injectable } from '@angular/core';
import { Response } from '@angular/http';

import { Observable } from 'rxjs/Observable';
import { AuthHttp } from 'angular2-jwt';
import * as moment from 'moment-mini';

import { GlobalsService } from './globals.service';

import { Session } from '../classes/session';

@Injectable()
export class SessionService {

  constructor(private globals_service: GlobalsService,
              public auth_http: AuthHttp) { }

  getSessions(): Observable<Session[]> {

    // console.log('getSessions');

    return this.auth_http.get(this.globals_service.site.restApiUrl + '/sessions')
      .map(this.extractData);
      // .catch(this.handleError);
  }

  private extractData(res: Response, error) {
    // console.log('error', error);
    let body = res.json();
    for (let session of body) {
      // console.log(session);
      session.start_display = moment(session.start).format('YYYY-MM-DD hh:mm:ss');
      session.end_display = moment(session.end).format('YYYY-MM-DD hh:mm:ss');
    }
    return body || {};
  }

  // private handleError(error: any) {
  //   console.error('An error occurred', error);
  //   return Observable.throw(error.message || error);
  // }

}
