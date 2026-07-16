/**
 * @generated SignedSource<<bb642b30e99cb6bdf032753f8710f36e>>
 * @lightSyntaxTransform
 * @nogrep
 */

/* tslint:disable */
/* eslint-disable */
// @ts-nocheck

import { ConcreteRequest } from 'relay-runtime';
export type reviewDashboardQuery$variables = Record<PropertyKey, never>;
export type reviewDashboardQuery$data = {
  readonly reviews: ReadonlyArray<{
    readonly createdAt: any;
    readonly diagnostics: {
      readonly blocks: number;
      readonly characters: number;
      readonly coverage: number;
      readonly parser: string;
      readonly warnings: ReadonlyArray<string>;
    } | null | undefined;
    readonly error: string | null | undefined;
    readonly filename: string;
    readonly findings: ReadonlyArray<{
      readonly category: string;
      readonly code: string;
      readonly confidence: number;
      readonly evidence: ReadonlyArray<{
        readonly cellRange: string | null | undefined;
        readonly page: number | null | undefined;
        readonly sheet: string | null | undefined;
        readonly source: string;
        readonly text: string;
      }>;
      readonly explanation: string;
      readonly recommendation: string;
      readonly requiresHumanReview: boolean;
      readonly severity: string;
      readonly title: string;
    }>;
    readonly id: string;
    readonly metrics: ReadonlyArray<{
      readonly confidence: number;
      readonly key: string;
      readonly label: string;
      readonly unit: string;
      readonly value: number;
    }>;
    readonly ruleVersion: string;
    readonly status: string;
  }>;
};
export type reviewDashboardQuery = {
  response: reviewDashboardQuery$data;
  variables: reviewDashboardQuery$variables;
};

const node: ConcreteRequest = (function(){
var v0 = {
  "alias": null,
  "args": null,
  "kind": "ScalarField",
  "name": "confidence",
  "storageKey": null
},
v1 = [
  {
    "alias": null,
    "args": [
      {
        "kind": "Literal",
        "name": "first",
        "value": 30
      }
    ],
    "concreteType": "ReviewType",
    "kind": "LinkedField",
    "name": "reviews",
    "plural": true,
    "selections": [
      {
        "alias": null,
        "args": null,
        "kind": "ScalarField",
        "name": "id",
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "kind": "ScalarField",
        "name": "filename",
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "kind": "ScalarField",
        "name": "status",
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "kind": "ScalarField",
        "name": "ruleVersion",
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "kind": "ScalarField",
        "name": "createdAt",
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "kind": "ScalarField",
        "name": "error",
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "concreteType": "DiagnosticType",
        "kind": "LinkedField",
        "name": "diagnostics",
        "plural": false,
        "selections": [
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "parser",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "blocks",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "characters",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "coverage",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "warnings",
            "storageKey": null
          }
        ],
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "concreteType": "MetricType",
        "kind": "LinkedField",
        "name": "metrics",
        "plural": true,
        "selections": [
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "key",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "label",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "value",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "unit",
            "storageKey": null
          },
          (v0/*: any*/)
        ],
        "storageKey": null
      },
      {
        "alias": null,
        "args": null,
        "concreteType": "FindingType",
        "kind": "LinkedField",
        "name": "findings",
        "plural": true,
        "selections": [
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "code",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "title",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "category",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "severity",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "explanation",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "recommendation",
            "storageKey": null
          },
          (v0/*: any*/),
          {
            "alias": null,
            "args": null,
            "kind": "ScalarField",
            "name": "requiresHumanReview",
            "storageKey": null
          },
          {
            "alias": null,
            "args": null,
            "concreteType": "EvidenceType",
            "kind": "LinkedField",
            "name": "evidence",
            "plural": true,
            "selections": [
              {
                "alias": null,
                "args": null,
                "kind": "ScalarField",
                "name": "text",
                "storageKey": null
              },
              {
                "alias": null,
                "args": null,
                "kind": "ScalarField",
                "name": "source",
                "storageKey": null
              },
              {
                "alias": null,
                "args": null,
                "kind": "ScalarField",
                "name": "page",
                "storageKey": null
              },
              {
                "alias": null,
                "args": null,
                "kind": "ScalarField",
                "name": "sheet",
                "storageKey": null
              },
              {
                "alias": null,
                "args": null,
                "kind": "ScalarField",
                "name": "cellRange",
                "storageKey": null
              }
            ],
            "storageKey": null
          }
        ],
        "storageKey": null
      }
    ],
    "storageKey": "reviews(first:30)"
  }
];
return {
  "fragment": {
    "argumentDefinitions": [],
    "kind": "Fragment",
    "metadata": null,
    "name": "reviewDashboardQuery",
    "selections": (v1/*: any*/),
    "type": "Query",
    "abstractKey": null
  },
  "kind": "Request",
  "operation": {
    "argumentDefinitions": [],
    "kind": "Operation",
    "name": "reviewDashboardQuery",
    "selections": (v1/*: any*/)
  },
  "params": {
    "cacheID": "87b2d606c98a8c42dcc07948e2ee9f8a",
    "id": null,
    "metadata": {},
    "name": "reviewDashboardQuery",
    "operationKind": "query",
    "text": "query reviewDashboardQuery {\n  reviews(first: 30) {\n    id\n    filename\n    status\n    ruleVersion\n    createdAt\n    error\n    diagnostics {\n      parser\n      blocks\n      characters\n      coverage\n      warnings\n    }\n    metrics {\n      key\n      label\n      value\n      unit\n      confidence\n    }\n    findings {\n      code\n      title\n      category\n      severity\n      explanation\n      recommendation\n      confidence\n      requiresHumanReview\n      evidence {\n        text\n        source\n        page\n        sheet\n        cellRange\n      }\n    }\n  }\n}\n"
  }
};
})();

(node as any).hash = "f49e1f20b5f95cf0d4fb8d77e7ea302a";

export default node;
