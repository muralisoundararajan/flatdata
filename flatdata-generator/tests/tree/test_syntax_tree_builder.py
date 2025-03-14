'''
 Copyright (c) 2017 HERE Europe B.V.
 See the LICENSE file in the root of this project for license details.
'''

import sys

from nose.tools import assert_equal, assert_is_instance, assert_raises, assert_true

sys.path.insert(0, "..")
from flatdata.generator.tree.errors import MissingSymbol, InvalidRangeName, InvalidRangeReference, \
    InvalidConstReference, InvalidConstValueReference, DuplicateInvalidValueReference, \
    InvalidStructInExplicitReference, OptionalRange
from flatdata.generator.tree.builder import build_ast
from flatdata.generator.tree.nodes.trivial import Namespace, Structure, Field, Constant, Enumeration, EnumerationValue
from flatdata.generator.tree.nodes.archive import Archive
from flatdata.generator.tree.nodes.explicit_reference import ExplicitReference
import flatdata.generator.tree.nodes.resources as res
from flatdata.generator.tree.nodes.resources import Vector, Multivector, RawData, Instance, BoundResource
from flatdata.generator.tree.nodes.references import ResourceReference, StructureReference, \
    FieldReference, ArchiveReference, BuiltinStructureReference, ConstantValueReference, \
    EnumerationReference, InvalidValueReference

def test_validating_archive_with_no_structure_defined_raises_missing_symbol_error():
    def __test(resource_type):
        with assert_raises(MissingSymbol):
            build_ast(
                """namespace foo{ archive A { resourceA : %s; } }""" % resource_type)

    for t in ["T", "vector< T >", "multivector< 33, V>"]:
        yield __test, t

def test_const_ref_with_mismatched_type():
    with assert_raises(InvalidConstReference):
        build_ast("""namespace foo{
            const u32 FOO = 10;
            struct A {
                @const(FOO)
                foo : u64 : 64;
            }
            }
            """)

def test_const_ref_with_too_few_bits():
    with assert_raises(InvalidConstValueReference):
        build_ast("""namespace foo{
            const u32 FOO = 16;
            struct A {
                @const(FOO)
                foo : u32 : 4;
            }
            }
            """)

def test_duplicate_optional():
    with assert_raises(DuplicateInvalidValueReference):
        build_ast("""namespace foo{
            const u32 FOO = 16;
            const u32 BAR = 16;
            struct A {
                @optional(FOO)
                @optional(BAR)
                foo : u32;
            }
            }
            """)

def test_range_with_duplicate_name():
    with assert_raises(InvalidRangeName):
        build_ast("""namespace foo{
            struct A {
                @range(ref_n)
                ref_n : u64 : 64;
            }
            }
            """)

def test_range_cannot_be_used_in_multivector():
    with assert_raises(InvalidRangeReference):
        build_ast("""namespace foo{
            struct A {
                @range(my_range)
                ref_n : u64 : 64;
            }
            archive R {
                resourceA : multivector< 40, A >;
            }
            }
            """)

def test_range_cannot_be_used_in_struct_resource():
    with assert_raises(InvalidRangeReference):
        build_ast("""namespace foo{
            struct A {
                @range(my_range)
                ref_n : u64 : 64;
            }
            archive R {
                resourceA : A;
            }
            }
            """)

def test_optional_range():
    with assert_raises(OptionalRange):
        build_ast("""namespace foo{
            const u32 NO_EDGES_REF = 200;
            struct Node {
                @range(edges_range)
                @optional( NO_EDGES_REF )
                first_edge_ref : u32;
            }
            }""")

def test_ranges_can_be_used_in_normally():
    build_ast("""namespace foo{
        struct A {
            @range(my_range)
            ref_n : u64 : 64;
        }

        @bound_implicitly( B: resourceA )
        archive R {
            @explicit_reference( A.ref_n, resourceA )
            resourceA : vector< A >;
        }
        }
        """)

def test_explicit_reference_decoration_fails_when_unknown_type_is_referenced():
    with assert_raises(MissingSymbol):
        build_ast("""namespace foo{
            struct A {
                refB : u64 : 64;
            }
            archive R {
                @explicit_reference( C.refB, resourceB )
                resourceA : vector< A >;
                resourceB : vector< A >;
            }
            }
            """)

def test_explicit_reference_decoration_fails_when_unknown_field_is_referenced():
    with assert_raises(MissingSymbol):
        build_ast("""namespace foo {
            struct A {
                refB : u64 : 64;
            }
            archive R {
                @explicit_reference( A.refX, resourceB )
                resourceA : vector< A >;
                resourceB : vector< A >;
            }
            }
            """)


def test_explicit_reference_decoration_fails_when_unknown_resource_is_referenced():
    with assert_raises(MissingSymbol):
        build_ast("""namespace foo{
            struct A {
                refB : u64 : 64;
            }
            archive R {
                @explicit_reference( A.refB, resourceB )
                resourceA : vector< A >;
            }
            }
            """)


def test_implicit_references_fail_on_unknown_resource():
    with assert_raises(MissingSymbol):
        build_ast("""namespace foo{
            struct A {
                refB : u64 : 64;
            }
            @bound_implicitly( B: resourceA, resourceC )
            archive R {
                resourceA : vector< A >;
                resourceB : vector< A >;
            }
            }
            """)


def test_multi_vector_references_builtin_type():
    tree = build_ast("""namespace n{
        struct T { t : u64 : 17; }
        archive A {
            r : multivector< 33, T >;
        }
        }
        """)
    assert_equal({
        ".n", ".n.T", ".n.T.t", ".n.A", ".n.A.r", ".n.A.r.@@n@T",
        ".n.A.r.@@n@_builtin@multivector@IndexType33",
        ".n._builtin", ".n._builtin.multivector",
        ".n._builtin.multivector.IndexType33", ".n._builtin.multivector.IndexType33.value"
    }, tree.symbols())


def test_duplicate_multivector_builtin_types_are_not_produced():
    tree = build_ast("""namespace n{
        struct T { t : u64 : 17; }
        archive A {
            r : multivector< 33, T >;
            r2 : multivector< 33, T >;
        }
        }
        """)
    assert_equal({
        ".n", ".n.T", ".n.T.t", ".n.A",
        ".n.A.r", ".n.A.r.@@n@T", ".n.A.r.@@n@_builtin@multivector@IndexType33",
        ".n.A.r2", ".n.A.r2.@@n@T", ".n.A.r2.@@n@_builtin@multivector@IndexType33",
        ".n._builtin", ".n._builtin.multivector",
        ".n._builtin.multivector.IndexType33", ".n._builtin.multivector.IndexType33.value"
    }, tree.symbols())


TREE_WITH_ALL_FEATURES = """
namespace ns{
    struct S0 {
        f0 : u64 : 64;
        f1 : u64 : 64;
    }

    struct S1 {
        @const(D)
        f0 : u64 : 64;
        // bla bla
        @optional(D)
        f1 : u64 : 64;
    }

    @bound_implicitly( b: A0.v0, A0.v1 )
    archive A0 {
        v0 : vector< S1 >;
        v1 : multivector< 14, S1 >;
    }

enum Enum1 : u16 : 4 {
 A = 1, B=13, C
}

struct XXX { e : Enum1; f : .ns.Enum1 : 4; }

    const u32 C = 0xFFFFFFF;

    const u64 D = 0xFFFFFFF;

    archive A1 {
        i : S0;
        v0 : vector< S1 >;

        @optional
        v1 : vector< S1 >;

        v2 : vector< XXX >;

        @explicit_reference( .ns.S0.f0, v0 )
        @explicit_reference( S0.f1, A1.v0 )
        @explicit_reference( S0.f1, .ns.A1.v1 )
        mv : multivector< 14, S0 >;
        rd : raw_data;
        a : archive A0;
    }
} // ns
"""


def test_all_flatdata_features_look_as_expected_in_fully_built_tree():
    tree = build_ast(TREE_WITH_ALL_FEATURES)

    assert_equal.__self__.maxDiff = None
    assert_equal({
        '.ns': Namespace,
        '.ns.A0': Archive,
        '.ns.A0.@@ns@C': ConstantValueReference,
        '.ns.A0.b': BoundResource,
        '.ns.A0.b.@@ns@A0@v0': ResourceReference,
        '.ns.A0.b.@@ns@A0@v1': ResourceReference,
        '.ns.A0.v0': Vector,
        '.ns.A0.v0.@@ns@S1': StructureReference,
        '.ns.A0.v1': Multivector,
        '.ns.A0.v1.@@ns@S1': StructureReference,
        '.ns.A0.v1.@@ns@_builtin@multivector@IndexType14': BuiltinStructureReference,
        '.ns.A1': Archive,
        '.ns.A1.@@ns@C': ConstantValueReference,
        '.ns.A1.a': res.Archive,
        '.ns.A1.a.@@ns@A0': ArchiveReference,
        '.ns.A1.i': Instance,
        '.ns.A1.i.@@ns@S0': StructureReference,
        '.ns.A1.mv': Multivector,
        '.ns.A1.mv.@@ns@S0': StructureReference,
        '.ns.A1.mv.@@ns@_builtin@multivector@IndexType14': BuiltinStructureReference,
        '.ns.A1.mv.er__ns_S0_f0_v0': ExplicitReference,
        '.ns.A1.mv.er__ns_S0_f0_v0.@@ns@A1@v0': ResourceReference,
        '.ns.A1.mv.er__ns_S0_f0_v0.@@ns@S0': StructureReference,
        '.ns.A1.mv.er__ns_S0_f0_v0.@@ns@S0@f0': FieldReference,
        '.ns.A1.mv.er_S0_f1_A1_v0': ExplicitReference,
        '.ns.A1.mv.er_S0_f1_A1_v0.@@ns@A1@v0': ResourceReference,
        '.ns.A1.mv.er_S0_f1_A1_v0.@@ns@S0': StructureReference,
        '.ns.A1.mv.er_S0_f1_A1_v0.@@ns@S0@f1': FieldReference,
        '.ns.A1.mv.er_S0_f1__ns_A1_v1': ExplicitReference,
        '.ns.A1.mv.er_S0_f1__ns_A1_v1.@@ns@A1@v1': ResourceReference,
        '.ns.A1.mv.er_S0_f1__ns_A1_v1.@@ns@S0': StructureReference,
        '.ns.A1.mv.er_S0_f1__ns_A1_v1.@@ns@S0@f1': FieldReference,
        '.ns.A1.rd': RawData,
        '.ns.A1.v0': Vector,
        '.ns.A1.v0.@@ns@S1': StructureReference,
        '.ns.A1.v1': Vector,
        '.ns.A1.v1.@@ns@S1': StructureReference,
        '.ns.A1.v2': Vector,
        '.ns.A1.v2.@@ns@XXX': StructureReference,
        '.ns.C': Constant,
        '.ns.D': Constant,
        '.ns.S0': Structure,
        '.ns.S0.f0': Field,
        '.ns.S0.f1': Field,
        '.ns.S1': Structure,
        '.ns.S1.f0': Field,
        '.ns.S1.f0.@@ns@D': ConstantValueReference,
        '.ns.S1.f1': Field,
        '.ns.S1.f1.@@ns@D': InvalidValueReference,
        '.ns.Enum1': Enumeration,
        '.ns.Enum1.A': EnumerationValue,
        '.ns.Enum1.B': EnumerationValue,
        '.ns.Enum1.C': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_0': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_10': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_11': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_12': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_15': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_2': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_3': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_4': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_5': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_6': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_7': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_8': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_9': EnumerationValue,
        '.ns.XXX': Structure,
        '.ns.XXX.e': Field,
        '.ns.XXX.e.@@ns@Enum1': EnumerationReference,
        '.ns.XXX.f': Field,
        '.ns.XXX.f.@@ns@Enum1': EnumerationReference,
        '.ns._builtin': Namespace,
        '.ns._builtin.multivector': Namespace,
        '.ns._builtin.multivector.IndexType14': Structure,
        '.ns._builtin.multivector.IndexType14.value': Field,
    }, tree.symbols(include_types=True))


def test_tree_with_all_features_schema_results_in_the_same_normalized_tree():
    tree = build_ast(TREE_WITH_ALL_FEATURES)
    schema = tree.schema(tree.find('.ns.A1'))
    generated_tree = build_ast(schema)
    assert_equal({
        '.ns': Namespace,
        '.ns.A0': Archive,
        '.ns.A0.@@ns@C': ConstantValueReference,
        '.ns.A0.b': BoundResource,
        '.ns.A0.b.@@ns@A0@v0': ResourceReference,
        '.ns.A0.b.@@ns@A0@v1': ResourceReference,
        '.ns.A0.v0': Vector,
        '.ns.A0.v0.@@ns@S1': StructureReference,
        '.ns.A0.v1': Multivector,
        '.ns.A0.v1.@@ns@_builtin@multivector@IndexType14': BuiltinStructureReference,
        '.ns.A0.v1.@@ns@S1': StructureReference,
        '.ns.A1': Archive,
        '.ns.A1.@@ns@C': ConstantValueReference,
        '.ns.A1.a': res.Archive,
        '.ns.A1.a.@@ns@A0': ArchiveReference,
        '.ns.A1.i': Instance,
        '.ns.A1.i.@@ns@S0': StructureReference,
        '.ns.A1.mv': Multivector,
        '.ns.A1.mv.@@ns@_builtin@multivector@IndexType14': BuiltinStructureReference,
        '.ns.A1.mv.@@ns@S0': StructureReference,
        '.ns.A1.mv.er__ns_S0_f0__ns_A1_v0': ExplicitReference,
        '.ns.A1.mv.er__ns_S0_f0__ns_A1_v0.@@ns@A1@v0': ResourceReference,
        '.ns.A1.mv.er__ns_S0_f0__ns_A1_v0.@@ns@S0': StructureReference,
        '.ns.A1.mv.er__ns_S0_f0__ns_A1_v0.@@ns@S0@f0': FieldReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v0': ExplicitReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v0.@@ns@A1@v0': ResourceReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v0.@@ns@S0': StructureReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v0.@@ns@S0@f1': FieldReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v1': ExplicitReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v1.@@ns@A1@v1': ResourceReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v1.@@ns@S0': StructureReference,
        '.ns.A1.mv.er__ns_S0_f1__ns_A1_v1.@@ns@S0@f1': FieldReference,
        '.ns.A1.rd': RawData,
        '.ns.A1.v0': Vector,
        '.ns.A1.v0.@@ns@S1': StructureReference,
        '.ns.A1.v1': Vector,
        '.ns.A1.v1.@@ns@S1': StructureReference,
        '.ns.A1.v2': Vector,
        '.ns.A1.v2.@@ns@XXX': StructureReference,
        '.ns.C': Constant,
        '.ns.D': Constant,
        '.ns.S0': Structure,
        '.ns.S0.f0': Field,
        '.ns.S0.f1': Field,
        '.ns.S1': Structure,
        '.ns.S1.f0': Field,
        '.ns.S1.f0.@@ns@D': ConstantValueReference,
        '.ns.S1.f1': Field,
        '.ns.S1.f1.@@ns@D': InvalidValueReference,
        '.ns.Enum1': Enumeration,
        '.ns.Enum1.A': EnumerationValue,
        '.ns.Enum1.B': EnumerationValue,
        '.ns.Enum1.C': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_0': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_10': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_11': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_12': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_15': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_2': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_3': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_4': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_5': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_6': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_7': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_8': EnumerationValue,
        '.ns.Enum1.UNKNOWN_VALUE_9': EnumerationValue,
        '.ns.XXX': Structure,
        '.ns.XXX.e': Field,
        '.ns.XXX.e.@@ns@Enum1': EnumerationReference,
        '.ns.XXX.f': Field,
        '.ns.XXX.f.@@ns@Enum1': EnumerationReference,
        '.ns._builtin': Namespace,
        '.ns._builtin.multivector': Namespace,
        '.ns._builtin.multivector.IndexType14': Structure,
        '.ns._builtin.multivector.IndexType14.value': Field,
    }, generated_tree.symbols(include_types=True))


def test_resource_types_are_populated_from_structure_references():
    def __test(schema, resource_type, properties):
        tree = build_ast("""namespace n{
            struct T {
                f0 : u8 : 1;
            }
            archive A {
                r : %s;
            }
            }
            """ % schema)

        a = tree.find(".n.A")
        assert_is_instance(a, Archive)
        r = a.find("A.r")
        assert_is_instance(r, resource_type)

        for k, values in properties.items():
            assert_true(hasattr(r, k))
            assert_equal([tree.find(v) for v in values], getattr(r, k))

    for values in [
        ("T", res.Instance, {"referenced_structures": [".n.A.r.@@n@T"]}),
        ("vector< T >", res.Vector, {"referenced_structures": [".n.A.r.@@n@T"]}),
        ("multivector< 33, T>", res.Multivector, {
            "referenced_structures": ['.n.A.r.@@n@_builtin@multivector@IndexType33',
                                      '.n.A.r.@@n@T']}),
        ("raw_data", res.RawData, {"referenced_structures": []})
    ]:
        yield __test, values[0], values[1], values[2]


def test_constants_are_referred_from_every_archive():
    tree = build_ast("""
namespace m {
    const u8 C = 17;
    }
namespace n.m {
    const u8 C = 13;
    }
namespace n{
    const u8 C = 42;

    struct T { f : u8 : 7; }
    archive A {
        resourceA : T;
    }
}""")
    tree.find(".n.A.@@n@C")
    tree.find(".n.A.@@m@C")
    tree.find(".n.A.@@n@m@C")

def test_explicit_reference_has_to_reference_struct_used_in_resource():
    with assert_raises(InvalidStructInExplicitReference):
        build_ast("""
            namespace prime {
            struct Factor {
                value : u32 : 32;
            }
            struct Number {
                @range(factors)
                first_factor_ref : u32;
            }
            
            archive Archive {
                @explicit_reference( Factor.value, factors )
                numbers : vector<Number>;
                factors : vector<Factor>;
            }
            } """)