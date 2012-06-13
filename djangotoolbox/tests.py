from .fields import ListField, SetField, DictField, EmbeddedModelField
from django.db import models, connections
from django.db.models import Q
from django.db.models.signals import post_save
from django.db.utils import DatabaseError
from django.dispatch.dispatcher import receiver
from django.test import TestCase
from django.utils import unittest

def count_calls(func):
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper

class Target(models.Model):
    index = models.IntegerField()

class Source(models.Model):
    target = models.ForeignKey(Target)
    index = models.IntegerField()

class ListModel(models.Model):
    integer = models.IntegerField(primary_key=True)
    floating_point = models.FloatField()
    names = ListField(models.CharField)
    names_with_default = ListField(models.CharField(max_length=500), default=[])
    names_nullable = ListField(models.CharField(max_length=500), null=True)

class OrderedListModel(models.Model):
    ordered_ints = ListField(models.IntegerField(max_length=500), default=[],
                             ordering=count_calls(lambda x:x), null=True)
    ordered_nullable = ListField(ordering=lambda x:x, null=True)

class SetModel(models.Model):
    setfield = SetField(models.IntegerField())

supports_dicts = getattr(connections['default'].features, 'supports_dicts', False)
if supports_dicts:
    class DictModel(models.Model):
        dictfield = DictField(models.IntegerField)
        dictfield_nullable = DictField(null=True)
        auto_now = DictField(models.DateTimeField(auto_now=True))

    class EmbeddedModelFieldModel(models.Model):
        simple = EmbeddedModelField('EmbeddedModel', null=True)
        simple_untyped = EmbeddedModelField(null=True)
        typed_list = ListField(EmbeddedModelField('SetModel'))
        typed_list2 = ListField(EmbeddedModelField('EmbeddedModel'))
        untyped_list = ListField(EmbeddedModelField())
        untyped_dict = DictField(EmbeddedModelField())
        ordered_list = ListField(EmbeddedModelField(), ordering=lambda obj: obj.index)

    class EmbeddedModel(models.Model):
        some_relation = models.ForeignKey(DictModel, null=True)
        someint = models.IntegerField(db_column='custom')
        auto_now = models.DateTimeField(auto_now=True)
        auto_now_add = models.DateTimeField(auto_now_add=True)

class FilterTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    names = [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]
    unordered_ints = [4, 2, 6, 1]

    def setUp(self):
        for i, float in enumerate(FilterTest.floats):
            ListModel(integer=i+1, floating_point=float, names=FilterTest.names[:i+1]).save()

    def test_startswith(self):
        self.assertEquals(dict([(entity.pk, entity.names) for entity in
                           ListModel.objects.filter(names__startswith='Sa')]),
                          dict([(3, ['Kakashi', 'Naruto', 'Sasuke',]),
                            (4, ['Kakashi', 'Naruto', 'Sasuke', 'Sakura',]), ]))

    def test_options(self):
        self.assertEqual([entity.names_with_default for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [[], []])

        self.assertEqual([entity.names_nullable for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [None, None])

    def test_default_value(self):
        # Make sure default value is copied
        ListModel().names_with_default.append(2)
        self.assertEqual(ListModel().names_with_default, [])

    def test_ordering(self):
        f = OrderedListModel._meta.fields[1]
        f.ordering.calls = 0

        # ensure no ordering happens on assignment
        obj = OrderedListModel()
        obj.ordered_ints = self.unordered_ints
        self.assertEqual(f.ordering.calls, 0)

        obj.save()
        self.assertEqual(OrderedListModel.objects.get().ordered_ints,
                         sorted(self.unordered_ints))
        # ordering should happen only once, i.e. the order function may be
        # called N times at most (N being the number of items in the list)
        self.assertLessEqual(f.ordering.calls, len(self.unordered_ints))

    def test_gt(self):
        # test gt on list
        self.assertEquals(dict([(entity.pk, entity.names) for entity in
                           ListModel.objects.filter(names__gt='Kakashi')]),
                          dict([(2, [u'Kakashi', u'Naruto',]),
                            (3, [u'Kakashi', u'Naruto', u'Sasuke',]),
                            (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]), ]))

    def test_lt(self):
        # test lt on list
        self.assertEquals(dict([(entity.pk, entity.names) for entity in
                           ListModel.objects.filter(names__lt='Naruto')]),
                          dict([(1, [u'Kakashi',]), (2, [u'Kakashi', u'Naruto',]),
                            (3, [u'Kakashi', u'Naruto', u'Sasuke',]),
                            (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]), ]))

    def test_gte(self):
        # test gte on list
        self.assertEquals(dict([(entity.pk, entity.names) for entity in
                           ListModel.objects.filter(names__gte='Sakura')]),
                          dict([(3, [u'Kakashi', u'Naruto', u'Sasuke',]),
                            (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]), ]))

    def test_lte(self):
        # test lte on list
        self.assertEquals(dict([(entity.pk, entity.names) for entity in
                           ListModel.objects.filter(names__lte='Kakashi')]),
                          dict([(1, [u'Kakashi',]), (2, [u'Kakashi', u'Naruto',]),
                            (3, [u'Kakashi', u'Naruto', u'Sasuke',]),
                            (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]), ]))

    def test_equals(self):
        # test equality filter on list
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names='Sakura')],
                          [[u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

        # test with additonal pk filter (for DBs that have special pk queries)
        query = ListModel.objects.filter(names='Sakura')
        self.assertEquals(query.get(pk=query[0].pk).names,
                          [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',])

    def test_is_null(self):
        self.assertEquals(ListModel.objects.filter(
            names__isnull=True).count(), 0)

    def test_exclude(self):
        self.assertEquals(dict([(entity.pk, entity.names) for entity in
                           ListModel.objects.all().exclude(
                            names__lt='Sakura')]),
                          dict([(3, [u'Kakashi', u'Naruto', u'Sasuke',]),
                           (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]), ]))

    def test_chained_filter(self):
        self.assertEquals([entity.names for entity in
                          ListModel.objects.filter(names='Sasuke').filter(
                            names='Sakura')], [['Kakashi', 'Naruto',
                            'Sasuke', 'Sakura'],])

        self.assertEquals([entity.names for entity in
                          ListModel.objects.filter(names__startswith='Sa').filter(
                            names='Sakura')], [['Kakashi', 'Naruto',
                            'Sasuke', 'Sakura']])

        # test across multiple columns. On app engine only one filter is allowed
        # to be an inequality filter
        self.assertEquals([entity.names for entity in
                          ListModel.objects.filter(floating_point=9.1).filter(
                            names__startswith='Sa')], [['Kakashi', 'Naruto',
                            'Sasuke',],])

    def test_setfield(self):
        setdata = [1, 2, 3, 2, 1]
        # At the same time test value conversion
        SetModel(setfield=map(str, setdata)).save()
        item = SetModel.objects.filter(setfield=3)[0]
        self.assertEqual(item.setfield, set(setdata))
        # This shouldn't raise an error because the default value is
        # an empty list
        SetModel().save()

    @unittest.skipIf(not supports_dicts, "Backend doesn't support dicts")
    def test_dictfield(self):
        DictModel(dictfield=dict(a=1, b='55', foo=3.14),
                  auto_now={'a' : None}).save()
        item = DictModel.objects.get()
        self.assertEqual(item.dictfield, {u'a' : 1, u'b' : 55, u'foo' : 3})

        dt = item.auto_now['a']
        self.assertNotEqual(dt, None)
        item.save()
        self.assertGreater(DictModel.objects.get().auto_now['a'], dt)
        item.delete()

        # Saving empty dicts shouldn't throw errors
        DictModel().save()
        # Regression tests for djangoappengine issue #39
        DictModel.add_to_class('new_dict_field', DictField())
        DictModel.objects.get()

    def test_Q_objects(self):
        self.assertEquals([entity.names for entity in
            ListModel.objects.exclude(Q(names__lt='Sakura') | Q(names__gte='Sasuke'))],
                [['Kakashi', 'Naruto', 'Sasuke', 'Sakura']])

class BaseModel(models.Model):
    pass

class ExtendedModel(BaseModel):
    name = models.CharField(max_length=20)

class BaseModelProxy(BaseModel):
    class Meta:
        proxy = True

class ExtendedModelProxy(ExtendedModel):
    class Meta:
        proxy = True

class ProxyTest(TestCase):
    def test_proxy(self):
        list(BaseModelProxy.objects.all())

    def test_proxy_with_inheritance(self):
        self.assertRaises(DatabaseError, lambda: list(ExtendedModelProxy.objects.all()))

class EmbeddedModelFieldTest(TestCase):
    def assertEqualDatetime(self, d1, d2):
        """ Compares d1 and d2, ignoring microseconds """
        self.assertEqual(d1.replace(microsecond=0), d2.replace(microsecond=0))

    def assertNotEqualDatetime(self, d1, d2):
        self.assertNotEqual(d1.replace(microsecond=0), d2.replace(microsecond=0))

    def _simple_instance(self):
        EmbeddedModelFieldModel.objects.create(simple=EmbeddedModel(someint='5'))
        return EmbeddedModelFieldModel.objects.get()

    def test_simple(self):
        instance = self._simple_instance()
        self.assertIsInstance(instance.simple, EmbeddedModel)
        # Make sure get_prep_value is called:
        self.assertEqual(instance.simple.someint, 5)
        # Primary keys should not be populated...
        self.assertEqual(instance.simple.id, None)
        # ... unless set explicitly.
        instance.simple.id = instance.id
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()
        self.assertEqual(instance.simple.id, instance.id)

    def _test_pre_save(self, instance, get_field):
        # Make sure field.pre_save is called for embedded objects
        from time import sleep
        instance.save()
        auto_now = get_field(instance).auto_now
        auto_now_add = get_field(instance).auto_now_add
        self.assertNotEqual(auto_now, None)
        self.assertNotEqual(auto_now_add, None)

        sleep(1) # FIXME
        instance.save()
        self.assertNotEqualDatetime(get_field(instance).auto_now,
                                    get_field(instance).auto_now_add)

        instance = EmbeddedModelFieldModel.objects.get()
        instance.save()
        # auto_now_add shouldn't have changed now, but auto_now should.
        self.assertEqualDatetime(get_field(instance).auto_now_add, auto_now_add)
        self.assertGreater(get_field(instance).auto_now, auto_now)

    def test_pre_save(self):
        obj = EmbeddedModelFieldModel(simple=EmbeddedModel())
        self._test_pre_save(obj, lambda instance: instance.simple)

    def test_pre_save_untyped(self):
        obj = EmbeddedModelFieldModel(simple_untyped=EmbeddedModel())
        self._test_pre_save(obj, lambda instance: instance.simple_untyped)

    def test_pre_save_in_list(self):
        obj = EmbeddedModelFieldModel(untyped_list=[EmbeddedModel()])
        self._test_pre_save(obj, lambda instance: instance.untyped_list[0])

    def test_pre_save_in_dict(self):
        obj = EmbeddedModelFieldModel(untyped_dict={'a': EmbeddedModel()})
        self._test_pre_save(obj, lambda instance: instance.untyped_dict['a'])

    def test_pre_save_list(self):
        # Also make sure auto_now{,add} works for embedded object *lists*.
        EmbeddedModelFieldModel.objects.create(typed_list2=[EmbeddedModel()])
        instance = EmbeddedModelFieldModel.objects.get()

        auto_now = instance.typed_list2[0].auto_now
        auto_now_add = instance.typed_list2[0].auto_now_add
        self.assertNotEqual(auto_now, None)
        self.assertNotEqual(auto_now_add, None)

        instance.typed_list2.append(EmbeddedModel())
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()

        self.assertEqualDatetime(instance.typed_list2[0].auto_now_add, auto_now_add)
        self.assertGreater(instance.typed_list2[0].auto_now, auto_now)
        self.assertNotEqual(instance.typed_list2[1].auto_now, None)
        self.assertNotEqual(instance.typed_list2[1].auto_now_add, None)

    def test_error_messages(self):
        for kwargs, expected in (
            ({'simple' : 42}, EmbeddedModel),
            ({'simple_untyped' : 42}, models.Model),
            ({'typed_list': [EmbeddedModel()]}, SetModel)
        ):
            self.assertRaisesRegexp(
                TypeError, "Expected instance of type %r" % expected,
                EmbeddedModelFieldModel(**kwargs).save
            )

    def test_typed_listfield(self):
        EmbeddedModelFieldModel.objects.create(
            typed_list=[SetModel(setfield=range(3)), SetModel(setfield=range(9))],
            ordered_list=[Target(index=i) for i in xrange(5, 0, -1)]
        )
        obj = EmbeddedModelFieldModel.objects.get()
        self.assertIn(5, obj.typed_list[1].setfield)
        self.assertEqual([target.index for target in obj.ordered_list],
                         range(1, 6))

    def test_untyped_listfield(self):
        EmbeddedModelFieldModel.objects.create(untyped_list=[
            EmbeddedModel(someint=7),
            OrderedListModel(ordered_ints=range(5, 0, -1)),
            SetModel(setfield=[1, 2, 2, 3])
        ])
        instances = EmbeddedModelFieldModel.objects.get().untyped_list
        for instance, cls in zip(instances, [EmbeddedModel, OrderedListModel, SetModel]):
            self.assertIsInstance(instance, cls)
        self.assertNotEqual(instances[0].auto_now, None)
        self.assertEqual(instances[1].ordered_ints, range(1, 6))

    def test_untyped_dict(self):
        EmbeddedModelFieldModel.objects.create(untyped_dict={
            'a' : SetModel(setfield=range(3)),
            'b' : DictModel(dictfield={'a' : 1, 'b' : 2}),
            'c' : DictModel(dictfield={}, auto_now={'y' : 1})
        })
        data = EmbeddedModelFieldModel.objects.get().untyped_dict
        self.assertIsInstance(data['a'], SetModel)
        self.assertNotEqual(data['c'].auto_now['y'], None)

    def test_foreignkey_in_embedded_object(self):
        simple = EmbeddedModel(some_relation=DictModel.objects.create())
        obj = EmbeddedModelFieldModel.objects.create(simple=simple)
        simple = EmbeddedModelFieldModel.objects.get().simple
        self.assertNotIn('some_relation', simple.__dict__)
        self.assertIsInstance(simple.__dict__['some_relation_id'], type(obj.id))
        self.assertIsInstance(simple.some_relation, DictModel)

EmbeddedModelFieldTest = unittest.skipIf(
    not supports_dicts, "Backend doesn't support dicts")(
    EmbeddedModelFieldTest)


class SignalTest(TestCase):
    def test_post_save(self):
        created = []
        @receiver(post_save, sender=SetModel)
        def handle(**kwargs):
            created.append(kwargs['created'])
        SetModel().save()
        self.assertEqual(created, [True])
        SetModel.objects.get().save()
        self.assertEqual(created, [True, False])
        qs = SetModel.objects.all()
        list(qs)[0].save()
        self.assertEqual(created, [True, False, False])
        list(qs)[0].save()
        self.assertEqual(created, [True, False, False, False])
        list(qs.select_related())[0].save()
        self.assertEqual(created, [True, False, False, False, False])

class SelectRelatedTest(TestCase):
    def test_select_related(self):
        target = Target(index=5)
        target.save()
        Source(target=target, index=8).save()
        source = Source.objects.all().select_related()[0]
        self.assertEqual(source.target.pk, target.pk)
        self.assertEqual(source.target.index, target.index)
        source = Source.objects.all().select_related('target')[0]
        self.assertEqual(source.target.pk, target.pk)
        self.assertEqual(source.target.index, target.index)
